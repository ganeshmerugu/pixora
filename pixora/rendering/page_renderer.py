"""Convert uploaded documents to page images (PNG) and compute field bounding boxes."""
from __future__ import annotations
import base64
import io
import os
from PIL import Image


def render_pages(file_bytes: bytes, filename: str, dpi: int = 150) -> list[dict]:
    """Return list of {page, width, height, image_base64, text_spans}."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return _render_pdf(file_bytes, dpi)
    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp",
               ".heic", ".heif", ".avif", ".gif", ".ico", ".svg"):
        return _render_image(file_bytes)
    return []


def _render_pdf(file_bytes: bytes, dpi: int) -> list[dict]:
    import pymupdf
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    scale = dpi / 72
    pages = []
    for i, page in enumerate(doc):
        mat = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        # Extract real text positions in pixel coordinates
        text_spans = []
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    bbox = span["bbox"]  # (x0, y0, x1, y1) in PDF points
                    text_spans.append({
                        "text": span["text"],
                        "x": bbox[0] * scale,
                        "y": bbox[1] * scale,
                        "width": (bbox[2] - bbox[0]) * scale,
                        "height": (bbox[3] - bbox[1]) * scale,
                    })

        pages.append({
            "page": i + 1,
            "width": pix.width,
            "height": pix.height,
            "image_base64": base64.b64encode(img_bytes).decode(),
            "text_spans": text_spans,
        })
    doc.close()
    return pages


def _render_image(file_bytes: bytes) -> list[dict]:
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return [{
        "page": 1,
        "width": img.width,
        "height": img.height,
        "image_base64": base64.b64encode(buf.getvalue()).decode(),
        "text_spans": [],
    }]


def compute_field_bboxes(
    extraction: dict,
    pages: list[dict],
    ocr_words: list[dict] | None = None,
) -> list[dict]:
    """Map each extracted field to a bounding box using real text positions from PDF or OCR."""
    # Collect all text spans with their pixel positions
    all_spans: list[dict] = []
    for p in pages:
        for sp in p.get("text_spans", []):
            all_spans.append({**sp, "page": p["page"]})

    # Also include OCR word-level bboxes
    if ocr_words:
        for w in ocr_words:
            b = w.get("bbox", {})
            if b and w.get("text", "").strip():
                all_spans.append({
                    "text": w["text"],
                    "x": b["x"], "y": b["y"],
                    "width": b["width"], "height": b["height"],
                    "page": b.get("page", 1),
                })

    if not all_spans:
        return []

    field_bboxes = []
    for field, value in extraction.items():
        if field.startswith("_") or value is None:
            continue
        val_str = str(value).strip()
        if not val_str:
            continue

        bbox = _match_value_to_spans(val_str, all_spans)
        if bbox:
            field_bboxes.append({
                "field": field,
                "value": val_str,
                "page": bbox["page"],
                "x": bbox["x"],
                "y": bbox["y"],
                "width": bbox["width"],
                "height": bbox["height"],
            })

    return field_bboxes


def _match_value_to_spans(value: str, spans: list[dict]) -> dict | None:
    """Find the span(s) that contain the extracted value using multi-strategy matching."""
    value_lower = value.lower().strip()
    val_norm = _normalize_for_match(value)

    # Strategy 1: exact match against a single span
    for sp in spans:
        if value_lower == sp["text"].lower().strip():
            return _pad_bbox(sp)

    # Strategy 2: value is contained within a single span
    for sp in spans:
        if value_lower in sp["text"].lower():
            return _pad_bbox(sp)

    # Strategy 3: normalized match (strip punctuation, collapse whitespace)
    for sp in spans:
        if val_norm and val_norm in _normalize_for_match(sp["text"]):
            return _pad_bbox(sp)

    # Strategy 4: multi-span merge — find all spans whose words overlap with value words
    value_words = set(value_lower.split())
    if len(value_words) >= 1:
        best_span = None
        best_overlap = 0
        for sp in spans:
            sp_text = sp["text"].strip()
            if not sp_text:
                continue
            sp_lower = sp_text.lower()
            if sp_lower in value_lower or value_lower in sp_lower:
                overlap = len(sp_text)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_span = sp
            else:
                sp_words = set(sp_lower.split())
                overlap = len(value_words & sp_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_span = sp

        if best_span and best_overlap >= 1:
            line_y = best_span["y"]
            line_h = max(best_span["height"], 5)

            matching_spans = []
            for sp in spans:
                if abs(sp["y"] - line_y) < line_h * 0.7:
                    sp_lower = sp["text"].strip().lower()
                    sp_words = set(sp_lower.split())
                    if sp_lower and (sp_lower in value_lower or value_lower in sp_lower
                                     or len(value_words & sp_words) > 0):
                        matching_spans.append(sp)

            if matching_spans:
                x_min = min(s["x"] for s in matching_spans)
                y_min = min(s["y"] for s in matching_spans)
                x_max = max(s["x"] + s["width"] for s in matching_spans)
                y_max = max(s["y"] + s["height"] for s in matching_spans)
                return _pad_bbox({
                    "x": x_min, "y": y_min,
                    "width": x_max - x_min, "height": y_max - y_min,
                    "page": best_span.get("page", 1),
                })
            return _pad_bbox(best_span)

    # Strategy 5: fuzzy single-word match using character overlap
    if len(value_lower) >= 3:
        best_sp = None
        best_ratio = 0.0
        for sp in spans:
            sp_lower = sp["text"].strip().lower()
            if not sp_lower:
                continue
            shorter = min(len(value_lower), len(sp_lower))
            longer = max(len(value_lower), len(sp_lower))
            common = sum(1 for a, b in zip(value_lower, sp_lower) if a == b)
            ratio = common / longer if longer > 0 else 0
            if ratio > best_ratio and ratio >= 0.6:
                best_ratio = ratio
                best_sp = sp
        if best_sp:
            return _pad_bbox(best_sp)

    return None


def _normalize_for_match(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _pad_bbox(span: dict, pad: float = 3) -> dict:
    return {
        "x": max(span["x"] - pad, 0),
        "y": max(span["y"] - pad, 0),
        "width": span["width"] + pad * 2,
        "height": span["height"] + pad * 2,
        "page": span.get("page", 1),
    }
