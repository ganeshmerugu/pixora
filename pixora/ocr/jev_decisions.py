"""Jev Decision Layer — replaces all hardcoded thresholds with calibrated probabilities.

OCR = eyes (exact characters + positions)
VLM = brain (structure + meaning)
Jev = judge (fast calibrated decisions, 193x faster than LLM)

Every pipeline decision that was a hardcoded threshold is now a Jev call:
  "quality < 0.4" → Jev Noul: "Is this OCR text readable?" P=0.87
  "similarity > 0.5" → Jev Noul: "Is this OCR word the same as this VLM value?" P=0.92
  "escalate to VLM" → Jev Noul: "Does this document need VLM?" P=0.95

Cost: ~$0.000042 per decision = 50 decisions per doc = $0.002/doc
vs Gemini VLM call = $0.001/doc → Jev is 50 decisions for 2x the cost of 1 VLM call
→ Use Jev only for the 5 highest-impact decisions, not all 50
"""
from __future__ import annotations
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from typesafe_sdk import AsyncTypeSafeClient, Noul, Choice, Score, Box, Image as JevImage
    HAS_JEV = True
except ImportError:
    HAS_JEV = False


def _get_key() -> str:
    import os
    key = os.environ.get("TYPESAFE_API_KEY", "") or os.environ.get("PIXORA_TYPESAFE_API_KEY", "")
    if not key:
        try:
            from pixora.config.settings import settings
            key = settings.typesafe_api_key
        except Exception:
            pass
    return key


def is_available() -> bool:
    return HAS_JEV and bool(_get_key())


# ══════════════════════════════════════════════════════════════
# DECISION 1: Should we escalate to VLM?
# Replaces: "if estimate_text_quality(ocr_text) < 0.4"
# ══════════════════════════════════════════════════════════════

async def should_escalate_to_vlm(ocr_text: str) -> tuple[bool, float]:
    """Ask Jev: is this OCR text good enough, or do we need VLM?
    Returns (should_escalate, confidence)."""
    if not is_available():
        from pixora.ocr.smart_pipeline import estimate_text_quality
        q = estimate_text_quality(ocr_text)
        return q < 0.4, 1.0 - q

    try:
        async with AsyncTypeSafeClient(api_key=_get_key()) as client:
            result = await client.system_one(
                model="jev-1",
                state=f"OCR extracted text:\n{ocr_text[:2000]}",
                questions={
                    "readable": Noul(
                        instructions="Is this OCR text clean and readable? (not garbled, not missing words, correct characters)",
                    ),
                    "needs_vlm": Noul(
                        instructions="Does this text have structural problems (wrong reading order, collapsed columns, merged fields) that need visual understanding to fix?",
                    ),
                },
            )
        readable = result.nouls["readable"].noul
        needs_vlm = result.nouls["needs_vlm"].noul
        should_escalate = readable < 0.5 or needs_vlm > 0.6
        confidence = max(1.0 - readable, needs_vlm)
        return should_escalate, round(confidence, 3)

    except Exception as exc:
        logger.debug("jev_decisions: escalation check failed: %s", exc)
        from pixora.ocr.smart_pipeline import estimate_text_quality
        q = estimate_text_quality(ocr_text)
        return q < 0.4, 1.0 - q


# ══════════════════════════════════════════════════════════════
# DECISION 2: Is this VLM extraction grounded in OCR text?
# Replaces: _verify_against_ocr() string matching
# ══════════════════════════════════════════════════════════════

async def verify_extraction_grounded(
    ocr_text: str,
    extraction: dict[str, Any],
) -> dict[str, dict]:
    """Ask Jev for each field: is this value grounded in the OCR text?
    Returns {field_name: {grounded: bool, probability: float}}."""
    results: dict[str, dict] = {}

    if not is_available():
        # Fallback: string matching
        ocr_lower = ocr_text.lower()
        for k, v in extraction.items():
            if k.startswith("_") or v is None:
                continue
            val_lower = str(v).lower().strip()
            found = val_lower in ocr_lower
            results[k] = {"grounded": found, "probability": 1.0 if found else 0.3}
        return results

    # Batch all fields into one Jev call (efficient)
    questions = {}
    field_keys = []
    for k, v in extraction.items():
        if k.startswith("_") or v is None:
            continue
        val_str = str(v).strip()
        if len(val_str) < 2:
            continue
        q_key = f"grounded_{k}"[:50]
        questions[q_key] = Noul(
            instructions=f"Is the value '{val_str}' present or strongly implied in the OCR text?",
        )
        field_keys.append((k, q_key))

    if not questions:
        return results

    try:
        async with AsyncTypeSafeClient(api_key=_get_key()) as client:
            result = await client.system_one(
                model="jev-1",
                state=f"OCR text from document:\n{ocr_text[:3000]}",
                questions=questions,
            )

        for field_name, q_key in field_keys:
            noul = result.nouls.get(q_key)
            if noul:
                results[field_name] = {
                    "grounded": noul.noul > 0.5,
                    "probability": round(noul.noul, 3),
                }
            else:
                results[field_name] = {"grounded": True, "probability": 0.5}

    except Exception as exc:
        logger.debug("jev_decisions: grounding check failed: %s", exc)
        ocr_lower = ocr_text.lower()
        for k, v in extraction.items():
            if k.startswith("_") or v is None:
                continue
            results[k] = {"grounded": str(v).lower() in ocr_lower, "probability": 0.5}

    return results


# ══════════════════════════════════════════════════════════════
# DECISION 3: What type is each field? (drives normalization)
# Replaces: keyword hints in post_normalize.py
# ══════════════════════════════════════════════════════════════

async def classify_fields(extraction: dict[str, Any]) -> dict[str, dict]:
    """Ask Jev: what type is each field? Returns {field: {type, confidence}}."""
    results: dict[str, dict] = {}

    if not is_available():
        from pixora.ocr.post_normalize import DATE_FIELD_HINTS, AMOUNT_FIELD_HINTS, NAME_FIELD_HINTS
        for k in extraction:
            if k.startswith("_"):
                continue
            kl = k.lower()
            if any(h in kl for h in DATE_FIELD_HINTS):
                results[k] = {"type": "date", "confidence": 0.8}
            elif any(h in kl for h in AMOUNT_FIELD_HINTS):
                results[k] = {"type": "amount", "confidence": 0.8}
            elif any(h in kl for h in NAME_FIELD_HINTS):
                results[k] = {"type": "name", "confidence": 0.8}
            else:
                results[k] = {"type": "text", "confidence": 0.5}
        return results

    questions = {}
    field_keys = []
    for k, v in extraction.items():
        if k.startswith("_") or v is None:
            continue
        q_key = f"type_{k}"[:50]
        questions[q_key] = Choice(
            instructions=f"What type of data is field '{k}' with value '{str(v)[:80]}'?",
            criteria={
                "date": "A date or timestamp",
                "amount": "A monetary amount",
                "name": "A person's name",
                "id": "An identifier or number",
                "address": "A physical address",
                "phone": "A phone number",
                "email": "An email address",
                "text": "General text",
            },
        )
        field_keys.append((k, q_key))

    if not questions:
        return results

    try:
        async with AsyncTypeSafeClient(api_key=_get_key()) as client:
            result = await client.system_one(
                model="jev-1",
                state="Classify the type of each extracted field.",
                questions=questions,
            )
        for field_name, q_key in field_keys:
            choice = result.choices.get(q_key)
            if choice:
                results[field_name] = {"type": choice.choice, "confidence": round(choice.confidence, 3)}

    except Exception as exc:
        logger.debug("jev_decisions: field classification failed: %s", exc)

    return results


# ══════════════════════════════════════════════════════════════
# DECISION 4: Rate extraction quality
# Replaces: scorer.py heuristic scoring
# ══════════════════════════════════════════════════════════════

async def rate_extraction_quality(
    ocr_text: str,
    extraction: dict[str, Any],
) -> dict:
    """Ask Jev: how good is this extraction? Returns {quality, confidence, score_0_1}."""
    if not is_available():
        from pixora.ocr.vlm_harness import estimate_extraction_confidence
        conf = estimate_extraction_confidence(extraction)
        return {"quality": "good" if conf > 0.7 else "acceptable", "confidence": conf, "score_0_1": conf}

    fields_str = "\n".join(f"  {k}: {v}" for k, v in extraction.items() if not k.startswith("_") and v)

    try:
        async with AsyncTypeSafeClient(api_key=_get_key()) as client:
            result = await client.system_one(
                model="jev-1",
                state=f"Source OCR text:\n{ocr_text[:2000]}\n\nExtracted fields:\n{fields_str[:2000]}",
                questions={
                    "quality": Score(
                        instructions="How accurate and complete is this extraction?",
                        criteria=["terrible", "poor", "acceptable", "good", "excellent"],
                    ),
                },
            )
        score = result.scores.get("quality")
        if score:
            score_map = {"terrible": 0.1, "poor": 0.3, "acceptable": 0.5, "good": 0.7, "excellent": 0.9}
            return {
                "quality": score.score,
                "confidence": round(score.confidence, 3),
                "score_0_1": score_map.get(score.score, 0.5),
            }
    except Exception as exc:
        logger.debug("jev_decisions: quality rating failed: %s", exc)

    return {"quality": "good", "confidence": 0.5, "score_0_1": 0.7}


# ══════════════════════════════════════════════════════════════
# DECISION 5: Locate fields in image (Box)
# Replaces: bbox_mapper.py algorithmic matching
# ══════════════════════════════════════════════════════════════

async def locate_fields_in_image(
    image_bytes: bytes,
    extraction: dict[str, Any],
    image_width: int,
    image_height: int,
) -> list[dict]:
    """Ask Jev Box: where is each field value in the image?"""
    if not is_available():
        return []

    bboxes: list[dict] = []

    for field_name, field_value in extraction.items():
        if field_name.startswith("_") or field_value is None:
            continue
        val_str = str(field_value).strip()
        if len(val_str) < 2:
            continue

        try:
            buf = io.BytesIO(image_bytes)
            async with AsyncTypeSafeClient(api_key=_get_key()) as client:
                result = await client.system_one(
                    model="jev-1",
                    state=[
                        f"Find the text '{val_str}' (field: {field_name}) in this document.",
                        JevImage(buf),
                    ],
                    questions={
                        "location": Box(
                            instructions=f"Locate '{val_str}' in the image.",
                        ),
                    },
                    headers={"TypeSafe-Danger-Zone-Images": "true"},
                )

            box = result.boxes.get("location")
            if box and box.confidence > 0.3:
                edges = box.box
                pad = int((1 - box.confidence) * 15)
                x = max(0, round(edges["left"] * image_width) - pad)
                y = max(0, round(edges["top"] * image_height) - pad)
                x2 = min(image_width, round(edges["right"] * image_width) + pad)
                y2 = min(image_height, round(edges["bottom"] * image_height) + pad)

                bboxes.append({
                    "field": field_name,
                    "x": x, "y": y,
                    "width": x2 - x, "height": y2 - y,
                    "page": 1,
                    "confidence": round(box.confidence, 3),
                })

        except Exception as exc:
            logger.debug("jev_decisions: Box failed for '%s': %s", field_name, exc)

    return bboxes
