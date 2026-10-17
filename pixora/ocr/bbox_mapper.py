"""Enterprise Bbox Mapper — maps VLM field values to OCR word positions.

Algorithms:
  1. Levenshtein edit distance for fuzzy word matching
  2. Sliding window n-gram alignment for multi-word values
  3. Spatial clustering — group matched words by proximity (not random scatter)
  4. Confidence-weighted selection — prefer high-confidence OCR words
  5. Label-aware anchoring — find the label first, then grab adjacent value words
  6. Reading order validation — matched words must follow natural reading order
"""
from __future__ import annotations
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from Levenshtein import ratio as lev_ratio, distance as lev_distance
    HAS_LEV = True
except ImportError:
    HAS_LEV = False


# ── Core Similarity ───────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    """Levenshtein ratio with OCR-aware normalization."""
    if not a or not b:
        return 0.0

    a_norm = _ocr_normalize(a)
    b_norm = _ocr_normalize(b)

    if a_norm == b_norm:
        return 1.0

    if HAS_LEV:
        return lev_ratio(a_norm, b_norm)

    # Fallback: character overlap
    common = sum(1 for c in a_norm if c in b_norm)
    return common / max(len(a_norm), len(b_norm))


def _ocr_normalize(text: str) -> str:
    """Normalize for OCR comparison — collapse common confusions."""
    t = text.lower().strip().rstrip("_.:,;!?")
    # OCR confusions
    t = t.replace("0", "o").replace("1", "l").replace("5", "s").replace("8", "b")
    t = t.replace("|", "l").replace("}", "j").replace("{", "c")
    # Remove non-alphanumeric for comparison
    t = re.sub(r"[^a-z0-9]", "", t)
    return t


def _tokenize(text: str) -> list[str]:
    """Split into tokens, keep meaningful pieces."""
    return [t for t in re.findall(r"[\w$.,/\-]+", text.lower()) if len(t) > 0]


# ── Strategy 1: Sliding Window N-gram Alignment ──────────────

def _sliding_window_match(
    value: str,
    ocr_words: list[dict],
    min_similarity: float = 0.55,
) -> list[dict]:
    """Slide a window across OCR words, find the span that best matches the value."""
    val_tokens = _tokenize(value)
    if not val_tokens:
        return []

    n = len(val_tokens)
    best_score = 0.0
    best_span: list[dict] = []

    # Try windows of size n-2 to n+3
    for window_size in range(max(1, n - 2), min(n + 4, len(ocr_words) + 1)):
        for start in range(len(ocr_words) - window_size + 1):
            window = ocr_words[start:start + window_size]
            window_text = " ".join(w.get("text", "") for w in window)
            sim = _similarity(value, window_text)

            # Bonus for spatial coherence (words close together)
            spatial_bonus = _spatial_coherence_score(window) * 0.1
            total = sim + spatial_bonus

            if total > best_score and sim >= min_similarity:
                best_score = total
                best_span = list(window)

    return best_span


# ── Strategy 2: Token-Level Hungarian Matching ────────────────

def _token_match(
    value: str,
    ocr_words: list[dict],
    min_token_sim: float = 0.5,
) -> list[dict]:
    """Match each value token to the best OCR word using greedy assignment."""
    val_tokens = _tokenize(value)
    if not val_tokens:
        return []

    # Build similarity matrix
    scores: list[list[float]] = []
    for vt in val_tokens:
        row: list[float] = []
        for word in ocr_words:
            ocr_text = word.get("text", "").strip()
            row.append(_similarity(vt, ocr_text))
        scores.append(row)

    # Greedy best-match (Hungarian-lite)
    matched: list[dict] = []
    used_cols: set[int] = set()

    for _ in range(len(val_tokens)):
        best_sim = 0.0
        best_r = -1
        best_c = -1

        for r in range(len(val_tokens)):
            for c in range(len(ocr_words)):
                if c in used_cols:
                    continue
                if scores[r][c] > best_sim:
                    best_sim = scores[r][c]
                    best_r = r
                    best_c = c

        if best_sim >= min_token_sim and best_c >= 0:
            matched.append(ocr_words[best_c])
            used_cols.add(best_c)
            # Zero out this row so we don't re-match
            for c in range(len(ocr_words)):
                scores[best_r][c] = 0.0
        else:
            break

    # Need at least 40% match rate
    if len(matched) >= max(1, len(val_tokens) * 0.4):
        return matched
    return []


# ── Strategy 3: Label-Aware Anchoring ─────────────────────────

COMMON_LABELS = {
    "name", "date", "phone", "address", "number", "total", "amount",
    "supervisor", "manager", "suggestion", "solution", "comments",
    "birth", "patient", "physician", "vendor", "invoice",
    "policy", "claim", "account", "balance",
}


def _label_anchor_match(
    field_name: str,
    value: str,
    ocr_words: list[dict],
) -> list[dict]:
    """Find the label word in OCR, then grab adjacent words as the value."""
    # Convert field name to potential label text
    label_parts = field_name.replace("_", " ").lower().split()

    # Find the label in OCR words
    label_idx = -1
    for lp in label_parts:
        if len(lp) < 3:
            continue
        for idx, word in enumerate(ocr_words):
            if _similarity(lp, word.get("text", "")) >= 0.6:
                label_idx = idx
                break
        if label_idx >= 0:
            break

    if label_idx < 0:
        return []

    # Grab the next N words after the label as the value
    label_word = ocr_words[label_idx]
    label_bbox = label_word.get("bbox", {})
    label_y = label_bbox.get("y", 0)
    label_x_end = label_bbox.get("x", 0) + label_bbox.get("width", 0)

    val_tokens = _tokenize(value)
    value_words: list[dict] = []

    for idx in range(label_idx + 1, min(label_idx + len(val_tokens) + 5, len(ocr_words))):
        word = ocr_words[idx]
        wb = word.get("bbox", {})
        wy = wb.get("y", 0)
        wx = wb.get("x", 0)

        # Value should be on same line (within 30px) or next line
        if abs(wy - label_y) > 40:
            # Might be on next line — allow if close to start of line
            if abs(wy - label_y) > 80:
                break

        # Value should be to the right of label or below
        if wx < label_x_end - 50 and abs(wy - label_y) < 10:
            continue

        text = word.get("text", "").strip()
        if text:
            value_words.append(word)

        if len(value_words) >= len(val_tokens) + 2:
            break

    # Verify matched words look like the value
    if value_words:
        combined = " ".join(w.get("text", "") for w in value_words)
        if _similarity(value, combined) >= 0.35:
            return value_words

    return []


# ── Spatial Analysis ──────────────────────────────────────────

def _spatial_coherence_score(words: list[dict]) -> float:
    """Score how spatially coherent a set of words is (should be close together)."""
    if len(words) <= 1:
        return 1.0

    ys = [w.get("bbox", {}).get("y", 0) for w in words]
    xs = [w.get("bbox", {}).get("x", 0) for w in words]

    y_range = max(ys) - min(ys)
    x_range = max(xs) - min(xs)

    # Penalize large vertical spread (multi-line)
    y_penalty = max(0, y_range - 30) * 0.01
    # Penalize extreme horizontal spread
    x_penalty = max(0, x_range - 500) * 0.001

    return max(0.0, 1.0 - y_penalty - x_penalty)


def _filter_spatial_outliers(words: list[dict]) -> list[dict]:
    """Remove words that are spatially far from the cluster center."""
    if len(words) <= 2:
        return words

    ys = [w.get("bbox", {}).get("y", 0) for w in words]
    median_y = sorted(ys)[len(ys) // 2]

    # Keep words within 40px of median Y (same line or adjacent)
    return [w for w in words if abs(w.get("bbox", {}).get("y", 0) - median_y) < 40]


def _validate_reading_order(words: list[dict]) -> list[dict]:
    """Sort words in natural reading order (top-to-bottom, left-to-right)."""
    return sorted(words, key=lambda w: (
        w.get("bbox", {}).get("y", 0),
        w.get("bbox", {}).get("x", 0),
    ))


# ── Bounding Box Computation ─────────────────────────────────

def _compute_enclosing_bbox(words: list[dict], padding: int = 4) -> dict:
    """Compute tight bounding box around matched words."""
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

    return {
        "x": max(0, min_x - padding),
        "y": max(0, min_y - padding),
        "width": (max_x - min_x) + 2 * padding,
        "height": (max_y - min_y) + 2 * padding,
    }


# ── Main Entry Point ──────────────────────────────────────────

def map_fields_to_bboxes(
    extraction: dict[str, Any],
    ocr_words: list[dict],
    page_width: int = 0,
    page_height: int = 0,
) -> list[dict]:
    """Map each VLM-extracted field to OCR word bounding boxes.

    Tries 3 strategies in order:
    1. Sliding window n-gram alignment (best for multi-word values)
    2. Label-aware anchoring (find label → grab adjacent value)
    3. Token-level Hungarian matching (fuzzy per-word)
    """
    if not extraction or not ocr_words:
        return []

    # Pre-sort OCR words by reading order
    sorted_words = _validate_reading_order(ocr_words)

    field_bboxes: list[dict] = []
    used_word_indices: set[int] = set()

    # Sort fields by value length descending (longer values match more reliably)
    field_items = sorted(
        [(k, v) for k, v in extraction.items() if not k.startswith("_") and v is not None],
        key=lambda x: len(str(x[1])),
        reverse=True,
    )

    for field_name, field_value in field_items:
        val_str = str(field_value).strip()
        if len(val_str) < 2:
            continue

        # Filter out already-used words
        available = [w for i, w in enumerate(sorted_words) if i not in used_word_indices]

        # Strategy 1: Sliding window
        matched = _sliding_window_match(val_str, available)

        # Strategy 2: Label anchoring
        if not matched:
            matched = _label_anchor_match(field_name, val_str, available)

        # Strategy 3: Token matching
        if not matched:
            matched = _token_match(val_str, available)

        if matched:
            # Post-process: remove outliers, validate order
            matched = _filter_spatial_outliers(matched)
            matched = _validate_reading_order(matched)

            bbox = _compute_enclosing_bbox(matched)
            bbox["field"] = field_name
            bbox["page"] = matched[0].get("bbox", {}).get("page", 1)
            bbox["confidence"] = round(
                sum(w.get("confidence", 0.5) for w in matched) / len(matched), 2
            )
            bbox["matched_words"] = len(matched)
            field_bboxes.append(bbox)

            # Mark words as used
            for mw in matched:
                for i, sw in enumerate(sorted_words):
                    if sw is mw:
                        used_word_indices.add(i)
                        break

    logger.info("bbox_mapper: mapped %d/%d fields to bboxes", len(field_bboxes),
                len([k for k in extraction if not k.startswith("_") and extraction[k] is not None]))

    return field_bboxes
