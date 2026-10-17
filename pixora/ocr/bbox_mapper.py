"""Bbox Mapper — maps VLM-extracted field values to OCR word positions.

VLM gives: {"name": "M. Hamann, P. Harper, P. Martinez"}
OCR gives: [("Harann", x=237, y=273), ("Harper_", x=315, y=271), ("Hartinez", x=391, y=271)]

This module fuzzy-matches VLM values to OCR words and computes
a bounding box that covers all matched words for each field.
"""
from __future__ import annotations
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def map_fields_to_bboxes(
    extraction: dict[str, Any],
    ocr_words: list[dict],
    page_width: int = 0,
    page_height: int = 0,
) -> list[dict]:
    """Map each extracted field value to a bounding box from OCR words.

    Returns list of {field, x, y, width, height, page, confidence}.
    """
    if not extraction or not ocr_words:
        return []

    field_bboxes: list[dict] = []

    for field_name, field_value in extraction.items():
        if field_name.startswith("_") or field_value is None:
            continue

        val_str = str(field_value).strip()
        if len(val_str) < 2:
            continue

        # Find OCR words that match this field value
        matched_words = _find_matching_words(val_str, ocr_words)

        if matched_words:
            bbox = _compute_enclosing_bbox(matched_words)
            bbox["field"] = field_name
            bbox["page"] = matched_words[0].get("bbox", {}).get("page", 1)
            bbox["confidence"] = sum(w.get("confidence", 0.5) for w in matched_words) / len(matched_words)
            field_bboxes.append(bbox)

    return field_bboxes


def _find_matching_words(value: str, ocr_words: list[dict]) -> list[dict]:
    """Find OCR words that correspond to a field value using multi-strategy matching."""

    val_lower = value.lower().strip()
    val_tokens = _tokenize(val_lower)

    if not val_tokens:
        return []

    # Strategy 1: Exact substring match — find consecutive words that contain the value
    result = _match_consecutive(val_lower, ocr_words)
    if result:
        return result

    # Strategy 2: Token-level fuzzy match — match individual words
    result = _match_tokens(val_tokens, ocr_words)
    if result:
        return result

    # Strategy 3: First significant word match — at least locate the field
    result = _match_first_word(val_tokens, ocr_words)
    if result:
        return result

    return []


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w$.,/\-]+", text.lower()) if len(w) > 0]


def _normalize_ocr(text: str) -> str:
    """Normalize OCR text for fuzzy comparison."""
    t = text.lower().strip().rstrip("_.:,;")
    t = t.replace("0", "o").replace("1", "l").replace("5", "s")
    return t


def _normalize_vlm(text: str) -> str:
    """Normalize VLM text for fuzzy comparison."""
    t = text.lower().strip()
    t = t.replace("0", "o").replace("1", "l").replace("5", "s")
    return t


def _char_similarity(a: str, b: str) -> float:
    """Quick character-level similarity without Levenshtein."""
    if not a or not b:
        return 0.0
    a_norm = _normalize_ocr(a)
    b_norm = _normalize_vlm(b)
    if a_norm == b_norm:
        return 1.0
    # Character overlap
    common = sum(1 for c in a_norm if c in b_norm)
    return common / max(len(a_norm), len(b_norm))


def _match_consecutive(value: str, ocr_words: list[dict]) -> list[dict]:
    """Try to find a sequence of OCR words that together form the value."""
    # Build running text from OCR words and find where value appears
    for start_idx in range(len(ocr_words)):
        accumulated = ""
        matched = []
        for j in range(start_idx, min(start_idx + 20, len(ocr_words))):
            word = ocr_words[j]
            text = word.get("text", "").strip()
            if not text:
                continue
            accumulated += (" " + text) if accumulated else text
            matched.append(word)

            acc_lower = accumulated.lower()
            val_lower = value.lower()

            # Check if accumulated text contains the value
            if val_lower in acc_lower or _char_similarity(acc_lower, val_lower) > 0.7:
                return matched

            # If accumulated is already longer than value, stop
            if len(accumulated) > len(value) * 1.5:
                break

    return []


def _match_tokens(val_tokens: list[str], ocr_words: list[dict]) -> list[dict]:
    """Match individual value tokens to OCR words using fuzzy matching."""
    matched: list[dict] = []
    used_indices: set[int] = set()

    for vt in val_tokens:
        if len(vt) <= 1:
            continue
        best_score = 0.0
        best_idx = -1

        for idx, word in enumerate(ocr_words):
            if idx in used_indices:
                continue
            ocr_text = word.get("text", "").strip()
            if not ocr_text:
                continue

            sim = _char_similarity(vt, ocr_text)
            if sim > best_score and sim >= 0.5:
                best_score = sim
                best_idx = idx

        if best_idx >= 0:
            matched.append(ocr_words[best_idx])
            used_indices.add(best_idx)

    # Only return if we matched at least 40% of tokens
    if len(matched) >= max(1, len(val_tokens) * 0.4):
        return matched
    return []


def _match_first_word(val_tokens: list[str], ocr_words: list[dict]) -> list[dict]:
    """Last resort: match the first significant word of the value."""
    for vt in val_tokens:
        if len(vt) < 3:
            continue
        for word in ocr_words:
            ocr_text = word.get("text", "").strip()
            if _char_similarity(vt, ocr_text) >= 0.6:
                return [word]
    return []


def _compute_enclosing_bbox(words: list[dict]) -> dict:
    """Compute a single bounding box that encloses all matched words."""
    if not words:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    min_x = float("inf")
    min_y = float("inf")
    max_x = 0
    max_y = 0

    for word in words:
        bbox = word.get("bbox", {})
        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        w = bbox.get("width", 0)
        h = bbox.get("height", 0)

        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)

    padding = 4
    return {
        "x": max(0, min_x - padding),
        "y": max(0, min_y - padding),
        "width": (max_x - min_x) + 2 * padding,
        "height": (max_y - min_y) + 2 * padding,
    }
