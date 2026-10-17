"""Jev (TypeSafe AI) integration — discriminative decisions with calibrated probabilities.

Jev primitives used:
  - Box: locate fields in document images → pixel-accurate bboxes
  - Noul: "is this value grounded in OCR?" → hallucination detection
  - Choice: "what type is this field?" → field classification
  - Score: "how confident is this extraction?" → quality scoring

$42/billion tokens ≈ $0.004 per 1000 documents.
Set PIXORA_TYPESAFE_API_KEY to enable.
"""
from __future__ import annotations
import base64
import io
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    from typesafe_sdk import AsyncTypeSafeClient, Noul, Choice, Score, Box, Image as JevImage
    HAS_JEV = True
except ImportError:
    HAS_JEV = False


def _get_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "") or os.environ.get("PIXORA_TYPESAFE_API_KEY", "")
    if not key:
        try:
            from pixora.config.settings import settings
            key = settings.typesafe_api_key
        except Exception:
            pass
    return key


def is_jev_available() -> bool:
    return HAS_JEV and bool(_get_key())


def _get_client():
    if not HAS_JEV:
        return None
    key = _get_key()
    if not key:
        return None
    return AsyncTypeSafeClient(api_key=key)


# ── Box: Locate fields in document images ─────────────────────

async def locate_field_in_image(
    image_bytes: bytes,
    field_name: str,
    field_value: str,
    image_width: int,
    image_height: int,
) -> dict | None:
    """Use Jev Box to find where a field value appears in the document image.
    Returns {x, y, width, height, confidence} in pixels."""
    client = _get_client()
    if not client:
        return None

    try:
        buf = io.BytesIO(image_bytes)
        async with client:
            result = await client.system_one(
                model="jev-1",
                state=[
                    f"This is a document image. Find the text '{field_value}' which is the value of the field '{field_name}'.",
                    JevImage(buf),
                ],
                questions={
                    "location": Box(
                        instructions=f"Locate the text '{field_value}' in the document image.",
                    ),
                    "present": Noul(
                        instructions=f"Is the text '{field_value}' visible in this document image?",
                    ),
                },
                headers={"TypeSafe-Danger-Zone-Images": "true"},
            )

        box_result = result.boxes.get("location")
        noul_result = result.nouls.get("present")

        if not box_result:
            return None

        edges = box_result.box
        confidence = box_result.confidence
        is_present = noul_result.noul if noul_result else 0.5

        if is_present < 0.3:
            return None

        x = round(edges["left"] * image_width)
        y = round(edges["top"] * image_height)
        x2 = round(edges["right"] * image_width)
        y2 = round(edges["bottom"] * image_height)

        # Add padding for low confidence
        if confidence < 0.7:
            pad = int((1 - confidence) * 20)
            x = max(0, x - pad)
            y = max(0, y - pad)
            x2 = min(image_width, x2 + pad)
            y2 = min(image_height, y2 + pad)

        return {
            "x": x,
            "y": y,
            "width": x2 - x,
            "height": y2 - y,
            "confidence": round(confidence, 3),
            "present_probability": round(is_present, 3),
            "field": field_name,
            "page": 1,
        }

    except Exception as exc:
        logger.warning("jev: Box query failed for '%s': %s", field_name, exc)
        return None


async def locate_all_fields(
    image_bytes: bytes,
    extraction: dict[str, Any],
    image_width: int,
    image_height: int,
) -> list[dict]:
    """Locate all extracted fields in the document image using Jev Box."""
    if not is_jev_available():
        return []

    bboxes: list[dict] = []
    for field_name, field_value in extraction.items():
        if field_name.startswith("_") or field_value is None:
            continue
        val_str = str(field_value).strip()
        if len(val_str) < 2:
            continue

        bbox = await locate_field_in_image(image_bytes, field_name, val_str, image_width, image_height)
        if bbox:
            bboxes.append(bbox)

    logger.info("jev: located %d/%d fields", len(bboxes),
                len([k for k in extraction if not k.startswith("_") and extraction[k] is not None]))
    return bboxes


# ── Noul: Hallucination detection ─────────────────────────────

async def verify_field_grounded(
    ocr_text: str,
    field_name: str,
    field_value: str,
) -> dict:
    """Check if a VLM-extracted value is grounded in OCR text."""
    client = _get_client()
    if not client:
        return {"grounded": True, "confidence": 0.5}

    try:
        async with client:
            result = await client.system_one(
                model="jev-1",
                state=f"OCR text from document:\n{ocr_text[:3000]}",
                questions={
                    "grounded": Noul(
                        instructions=f"Is the value '{field_value}' (field: {field_name}) present or strongly implied in the OCR text above?",
                    ),
                },
            )

        noul = result.nouls.get("grounded")
        if noul:
            return {"grounded": noul.noul > 0.5, "confidence": round(noul.noul, 3)}

    except Exception as exc:
        logger.warning("jev: grounding check failed for '%s': %s", field_name, exc)

    return {"grounded": True, "confidence": 0.5}


# ── Choice: Field type classification ─────────────────────────

async def classify_field_type(field_name: str, field_value: str) -> dict:
    """Classify what type a field is (date, amount, name, id, etc.)."""
    client = _get_client()
    if not client:
        return {"type": "text", "confidence": 0.5}

    try:
        async with client:
            result = await client.system_one(
                model="jev-1",
                state=f"Field name: {field_name}\nField value: {field_value}",
                questions={
                    "field_type": Choice(
                        instructions="What type of data is this field?",
                        criteria={
                            "date": "A date or timestamp (e.g., 03/15/2024, January 15)",
                            "amount": "A monetary amount (e.g., $49,674.22, 1500.00)",
                            "name": "A person's name (e.g., John Doe, Dr. Smith)",
                            "id": "An identifier or number (e.g., INV-001, MRN-123)",
                            "address": "A physical address",
                            "phone": "A phone number",
                            "email": "An email address",
                            "text": "General text content",
                        },
                    ),
                },
            )

        choice = result.choices.get("field_type")
        if choice:
            return {"type": choice.choice, "confidence": round(choice.confidence, 3)}

    except Exception as exc:
        logger.warning("jev: field classification failed: %s", exc)

    return {"type": "text", "confidence": 0.5}


# ── Score: Extraction quality ─────────────────────────────────

async def score_extraction_quality(
    ocr_text: str,
    extraction: dict,
) -> dict:
    """Score overall extraction quality on a 5-level scale."""
    client = _get_client()
    if not client:
        return {"quality": "good", "confidence": 0.5}

    fields_summary = "\n".join(f"  {k}: {v}" for k, v in extraction.items() if not k.startswith("_") and v)

    try:
        async with client:
            result = await client.system_one(
                model="jev-1",
                state=f"OCR text:\n{ocr_text[:2000]}\n\nExtracted fields:\n{fields_summary[:2000]}",
                questions={
                    "quality": Score(
                        instructions="How accurate and complete is this extraction compared to the source text?",
                        criteria=["terrible", "poor", "acceptable", "good", "excellent"],
                    ),
                },
            )

        score = result.scores.get("quality")
        if score:
            return {"quality": score.score, "confidence": round(score.confidence, 3)}

    except Exception as exc:
        logger.warning("jev: quality scoring failed: %s", exc)

    return {"quality": "good", "confidence": 0.5}
