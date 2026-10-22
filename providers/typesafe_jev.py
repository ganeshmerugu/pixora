"""TypeSafe Jev provider — System One decision model for classification, extraction, and HITL routing.

Jev is NOT an LLM or VLM. It answers typed questions (Choice, Score, Noul) with
calibrated probabilities. It never generates text — only selects/scores from
options you provide, so it cannot hallucinate values.

Integration points in Pixora:
  1. Doc classification — Choice: pick doc type from list
  2. Pre-parsed value extraction — regex finds candidates, Choice picks the right one
  3. Confidence-gated HITL routing — Score + Noul with calibrated confidence
"""
from __future__ import annotations
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score
    HAS_TYPESAFE = True
except ImportError:
    HAS_TYPESAFE = False

DEFAULT_MODEL = "jev-latest"

DOC_TYPE_CRITERIA: dict[str, str] = {
    "invoice": "A bill for goods or services with amounts, vendor, and line items",
    "receipt": "Proof of payment with totals, date, and merchant",
    "contract": "Legal agreement between parties with terms, signatures, and clauses",
    "bank_statement": "Account summary with transactions, balances, and dates",
    "medical": "Medical records, prescriptions, lab results, or patient forms",
    "insurance": "Insurance policy, claim, or coverage document",
    "government": "Government-issued ID, certificate, permit, or official form",
    "tax_form": "Tax return, W-2, 1099, or tax-related document",
    "shipping": "Bill of lading, shipping label, or logistics document",
    "form": "A fillable form with checkboxes, text fields, or signatures",
    "letter": "General correspondence or memo",
    "report": "Structured report with sections, tables, or charts",
    "unknown": "None of the above categories fit",
}

EXTRACTION_QUALITY_LEVELS = [
    "Unusable: mostly garbage, wrong fields, or empty",
    "Poor: some fields correct but many errors or missing values",
    "Acceptable: most fields correct, minor errors tolerable",
    "Good: all key fields correct, minor formatting issues only",
    "Excellent: every field extracted accurately with correct values",
]

VALUE_CANDIDATE_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\(?\+?\d[\d\s()\-.]{6,}\d"),
    "amount": re.compile(r"[$€£¥]\s?\d[\d,]*(?:\.\d{2})?"),
    "date": re.compile(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b"),
    "id_number": re.compile(r"\b[A-Z]{2,5}[-#]?\d{3,}\b"),
    "percentage": re.compile(r"\b\d{1,3}(?:\.\d{1,2})?\s?%"),
}

NONE_SENTINEL = "__none__"


def is_available() -> bool:
    if not HAS_TYPESAFE:
        return False
    key = os.environ.get("TYPESAFE_API_KEY", os.environ.get("PIXORA_TYPESAFE_API_KEY", ""))
    return bool(key)


def _get_api_key() -> str:
    return os.environ.get("TYPESAFE_API_KEY", os.environ.get("PIXORA_TYPESAFE_API_KEY", ""))


# ── 1. Document Classification (Choice) ─────────────────────────


async def classify_document(
    text: str,
    image_bytes: bytes | None = None,
    custom_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not is_available():
        return {"doc_type": "unknown", "confidence": 0.0, "provider": "none"}

    criteria = custom_types or DOC_TYPE_CRITERIA

    async with AsyncTypeSafeClient(
        api_key=_get_api_key(),
        model=DEFAULT_MODEL,
    ) as client:
        response = await client.system_one(
            state=text[:8000],
            questions={
                "doc_type": Choice(
                    instructions="What type of document is this?",
                    criteria=criteria,
                ),
                "has_table": Noul(instructions="Does this document contain a table with rows and columns?"),
                "has_handwriting": Noul(instructions="Does this document contain handwritten text?"),
            },
        )

    doc_type_answer = response.choices["doc_type"]
    return {
        "doc_type": doc_type_answer.choice,
        "confidence": doc_type_answer.confidence,
        "probabilities": doc_type_answer.probabilities,
        "has_table": response.nouls["has_table"].noul,
        "has_handwriting": response.nouls["has_handwriting"].noul,
        "provider": "jev",
    }


# ── 2. Pre-Parsed Value Extraction (regex + Choice pick) ────────


def find_candidates(text: str, field_type: str) -> list[str]:
    pattern = VALUE_CANDIDATE_PATTERNS.get(field_type)
    if not pattern:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        span = match.group().strip()
        if span and span not in seen:
            seen.add(span)
            out.append(span)
    return out


async def pick_value(
    text: str,
    candidates: list[str],
    question: str,
) -> dict[str, Any]:
    if not is_available() or not candidates:
        return {"value": None, "confidence": 0.0}

    criteria = {c: None for c in candidates}
    criteria[NONE_SENTINEL] = "None of these is the requested value"

    async with AsyncTypeSafeClient(
        api_key=_get_api_key(),
        model=DEFAULT_MODEL,
    ) as client:
        response = await client.system_one(
            state=text[:8000],
            questions={
                "pick": Choice(instructions=question, criteria=criteria),
            },
        )

    answer = response.choices["pick"]
    chosen = answer.choice
    if chosen == NONE_SENTINEL:
        return {"value": None, "confidence": answer.confidence, "provider": "jev"}

    return {
        "value": chosen,
        "confidence": answer.confidence,
        "provider": "jev",
    }


_FIELD_TYPE_TO_JEV: dict[str, str] = {
    "CURRENCY": "amount",
    "DATE": "date",
    "NUMBER": "amount",
}

_NAME_HINT_TO_JEV: list[tuple[list[str], str]] = [
    (["email"], "email"),
    (["phone", "mobile", "fax", "tel"], "phone"),
    (["percent", "rate", "ratio"], "percentage"),
    (["number", "id", "pan", "aadhaar", "uid", "vin", "mrn", "ein", "ssn",
      "licence", "license", "passport", "tracking", "order", "invoice_number",
      "policy", "account"], "id_number"),
]


def schema_to_field_specs(schema_nodes: list[dict]) -> dict[str, dict[str, str]]:
    """Convert Pixora schema nodes to Jev field_specs for extract_fields_with_jev."""
    specs: dict[str, dict[str, str]] = {}
    for node in schema_nodes:
        name = node["name"]
        field_type = node.get("field_type", "STRING")
        description = node.get("description", name.replace("_", " "))

        jev_type = _FIELD_TYPE_TO_JEV.get(field_type)

        if not jev_type and field_type == "STRING":
            lower = name.lower()
            for keywords, jtype in _NAME_HINT_TO_JEV:
                if any(kw in lower for kw in keywords):
                    jev_type = jtype
                    break

        if not jev_type:
            continue

        specs[name] = {
            "type": jev_type,
            "question": f"Which value is the {description}?",
        }
    return specs


async def extract_all_candidates(text: str) -> dict[str, Any]:
    """Schema-less extraction: sweep all candidate types and let Jev pick."""
    if not is_available() or not text.strip():
        return {}

    results: dict[str, Any] = {}
    for jev_type, pattern in VALUE_CANDIDATE_PATTERNS.items():
        candidates = list({m.group().strip() for m in pattern.finditer(text)})
        if not candidates:
            continue
        picked = await pick_value(
            text, candidates,
            f"Which of these is the most important {jev_type} in this document?",
        )
        if picked.get("value"):
            results[jev_type] = picked["value"]
    return results


async def extract_fields_with_jev(
    text: str,
    field_specs: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Extract multiple fields using regex + Jev pick pattern.

    field_specs maps field_name -> {"type": "amount|date|email|...", "question": "..."}
    """
    results: dict[str, Any] = {}
    for field_name, spec in field_specs.items():
        field_type = spec.get("type", "")
        question = spec.get("question", f"Which value is the {field_name}?")
        candidates = find_candidates(text, field_type)
        if not candidates:
            results[field_name] = None
            continue
        picked = await pick_value(text, candidates, question)
        results[field_name] = picked.get("value")
    return results


# ── 3. Confidence-Gated HITL Routing ────────────────────────────


async def evaluate_extraction_quality(
    text: str,
    extraction: dict[str, Any],
) -> dict[str, Any]:
    if not is_available():
        return {"action": "accept", "confidence": 0.0, "provider": "none"}

    extraction_summary = "\n".join(f"{k}: {v}" for k, v in extraction.items() if v and not str(k).startswith("_"))

    state = f"DOCUMENT TEXT:\n{text[:4000]}\n\nEXTRACTED FIELDS:\n{extraction_summary}"

    async with AsyncTypeSafeClient(
        api_key=_get_api_key(),
        model=DEFAULT_MODEL,
    ) as client:
        response = await client.system_one(
            state=state,
            questions={
                "quality": Score(
                    instructions="How well were the fields extracted from this document?",
                    criteria=EXTRACTION_QUALITY_LEVELS,
                ),
                "has_errors": Noul(
                    instructions="Are there obvious extraction errors — wrong values, swapped fields, or missing critical data?",
                ),
                "needs_human": Noul(
                    instructions="Should a human review this extraction before it is used downstream?",
                ),
            },
        )

    quality = response.scores["quality"]
    has_errors = response.nouls["has_errors"].noul
    needs_human = response.nouls["needs_human"].noul

    # Confidence-gated routing
    score_idx = int(quality.score)
    confidence = quality.confidence

    if score_idx >= 3 and confidence >= 0.8 and has_errors < 0.3:
        action = "accept"
    elif score_idx <= 1 or has_errors > 0.7 or needs_human > 0.8:
        action = "reject"
    else:
        action = "review"

    return {
        "action": action,
        "quality_score": score_idx,
        "quality_level": EXTRACTION_QUALITY_LEVELS[score_idx] if 0 <= score_idx < len(EXTRACTION_QUALITY_LEVELS) else "unknown",
        "quality_confidence": confidence,
        "quality_probabilities": quality.probabilities,
        "has_errors_prob": has_errors,
        "needs_human_prob": needs_human,
        "provider": "jev",
    }


# ── 4. Field-Level Validation (Noul per field) ──────────────────


async def validate_fields(
    text: str,
    extraction: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not is_available() or not extraction:
        return {}

    questions: dict[str, Any] = {}
    field_list = [(k, v) for k, v in extraction.items() if v and not str(k).startswith("_")]

    for field_name, value in field_list[:20]:
        questions[f"valid_{field_name}"] = Noul(
            instructions=f'Is "{value}" a correct and plausible value for the field "{field_name}" in this document?',
        )

    if not questions:
        return {}

    async with AsyncTypeSafeClient(
        api_key=_get_api_key(),
        model=DEFAULT_MODEL,
    ) as client:
        response = await client.system_one(
            state=text[:6000],
            questions=questions,
        )

    results: dict[str, dict[str, Any]] = {}
    for field_name, value in field_list[:20]:
        noul = response.nouls[f"valid_{field_name}"].noul
        results[field_name] = {
            "value": value,
            "valid_prob": noul,
            "likely_correct": noul >= 0.5,
            "needs_review": 0.25 <= noul < 0.5,
            "likely_wrong": noul < 0.25,
        }

    return results
