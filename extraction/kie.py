"""Key Information Extraction (KIE) — BIO token classification on OCR output.

Rule-based baseline: regex patterns + spatial heuristics.
Optional transformer-based model (LayoutLM-style) when PyTorch available.

Spatial feature encoding per token:
  B_i = [x0/W, y0/H, x1/W, y1/H, w/W, h/H]
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.models.document import BoundingBox


class Entity(TypedDict, total=False):
    label: Required[str]
    value: Required[str]
    bio_tags: list[str]
    bbox: BoundingBox
    confidence: float
    word_indices: list[int]


class KIEWord(TypedDict, total=False):
    text: Required[str]
    bbox: Required[BoundingBox]
    confidence: float


LABEL_PATTERNS: dict[str, list[re.Pattern]] = {
    "INVOICE_NUM": [
        re.compile(r"(?:invoice|inv|bill)\s*(?:#|no|number|num)?\s*[:.]?\s*([A-Z0-9\-]{3,})", re.I),
    ],
    "DATE": [
        re.compile(r"(?:date|dated|dt)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I),
        re.compile(r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4})", re.I),
    ],
    "TOTAL": [
        re.compile(r"(?:total|amount\s*due|grand\s*total|balance\s*due)\s*[:.]?\s*\$?([\d,]+\.?\d*)", re.I),
    ],
    "SUBTOTAL": [
        re.compile(r"(?:subtotal|sub\s*total|net)\s*[:.]?\s*\$?([\d,]+\.?\d*)", re.I),
    ],
    "TAX": [
        re.compile(r"(?:tax|vat|gst|sales\s*tax)\s*[:.]?\s*\$?([\d,]+\.?\d*)", re.I),
    ],
    "VENDOR_NAME": [
        re.compile(r"(?:from|vendor|seller|company|billed\s*by)\s*[:.]?\s*(.+)", re.I),
    ],
    "CUSTOMER_NAME": [
        re.compile(r"(?:to|customer|buyer|bill\s*to|ship\s*to)\s*[:.]?\s*(.+)", re.I),
    ],
    "ADDRESS": [
        re.compile(r"(\d+\s+\w+\s+(?:St|Ave|Rd|Blvd|Dr|Ln|Way|Ct|Pl)\b.*)", re.I),
    ],
    "PHONE": [
        re.compile(r"(?:phone|tel|fax)\s*[:.]?\s*([\+\d\(\)\s\-\.]{7,})", re.I),
    ],
    "EMAIL": [
        re.compile(r"(?:email|e-mail)\s*[:.]?\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I),
    ],
}

LABEL_KEYWORDS: dict[str, list[str]] = {
    "INVOICE_NUM": ["invoice", "inv", "bill", "reference"],
    "DATE": ["date", "dated", "issued", "due"],
    "TOTAL": ["total", "amount due", "grand total", "balance"],
    "SUBTOTAL": ["subtotal", "sub total", "net"],
    "TAX": ["tax", "vat", "gst"],
    "VENDOR_NAME": ["from", "vendor", "seller", "company"],
    "CUSTOMER_NAME": ["to", "customer", "buyer", "bill to", "ship to"],
}


def _spatial_features(bbox: BoundingBox, page_w: float, page_h: float) -> list[float]:
    x0 = bbox["x"] / max(page_w, 1)
    y0 = bbox["y"] / max(page_h, 1)
    x1 = (bbox["x"] + bbox["width"]) / max(page_w, 1)
    y1 = (bbox["y"] + bbox["height"]) / max(page_h, 1)
    w = bbox["width"] / max(page_w, 1)
    h = bbox["height"] / max(page_h, 1)
    return [x0, y0, x1, y1, w, h]


class KIEExtractor:
    def __init__(self, custom_patterns: dict[str, list[re.Pattern]] | None = None):
        self.patterns = {**LABEL_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def extract(
        self,
        words: list[KIEWord],
        page_width: float = 0,
        page_height: float = 0,
    ) -> list[Entity]:
        full_text = " ".join(w["text"] for w in words)
        entities: list[Entity] = []
        found_labels: set[str] = set()

        for label, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(full_text):
                    value = match.group(1) if match.lastindex else match.group(0)
                    value = value.strip().rstrip(".,;:")
                    if not value:
                        continue

                    word_indices = self._find_word_indices(words, match.start(), match.end(), full_text)
                    bbox = self._merge_bboxes(words, word_indices)

                    entities.append(Entity(
                        label=label,
                        value=value,
                        bbox=bbox,
                        confidence=0.8,
                        word_indices=word_indices,
                    ))
                    found_labels.add(label)
                    break

        spatial_entities = self._spatial_extraction(words, found_labels, page_width, page_height)
        entities.extend(spatial_entities)

        return entities

    def _find_word_indices(
        self, words: list[KIEWord], char_start: int, char_end: int, full_text: str,
    ) -> list[int]:
        indices: list[int] = []
        pos = 0
        for i, w in enumerate(words):
            word_start = pos
            word_end = pos + len(w["text"])
            if word_end > char_start and word_start < char_end:
                indices.append(i)
            pos = word_end + 1
        return indices

    def _merge_bboxes(self, words: list[KIEWord], indices: list[int]) -> BoundingBox:
        if not indices:
            return BoundingBox(x=0, y=0, width=0, height=0, page=1)

        bboxes = [words[i]["bbox"] for i in indices if i < len(words)]
        if not bboxes:
            return BoundingBox(x=0, y=0, width=0, height=0, page=1)

        x_min = min(b["x"] for b in bboxes)
        y_min = min(b["y"] for b in bboxes)
        x_max = max(b["x"] + b["width"] for b in bboxes)
        y_max = max(b["y"] + b["height"] for b in bboxes)

        return BoundingBox(
            x=x_min, y=y_min,
            width=x_max - x_min, height=y_max - y_min,
            page=bboxes[0].get("page", 1),
        )

    def _spatial_extraction(
        self,
        words: list[KIEWord],
        found_labels: set[str],
        page_w: float,
        page_h: float,
    ) -> list[Entity]:
        entities: list[Entity] = []

        for i, word in enumerate(words):
            text_lower = word["text"].lower().strip(":. ")

            for label, keywords in LABEL_KEYWORDS.items():
                if label in found_labels:
                    continue

                for kw in keywords:
                    if kw in text_lower:
                        value_words = self._find_value_to_right(words, i, page_w)
                        if not value_words:
                            value_words = self._find_value_below(words, i)

                        if value_words:
                            value = " ".join(w["text"] for w in value_words)
                            bbox = self._merge_bboxes(
                                words,
                                [words.index(w) for w in value_words if w in words],
                            )
                            entities.append(Entity(
                                label=label, value=value.strip(),
                                bbox=bbox, confidence=0.6,
                            ))
                            found_labels.add(label)
                        break

        return entities

    def _find_value_to_right(
        self, words: list[KIEWord], key_idx: int, page_w: float,
    ) -> list[KIEWord]:
        key = words[key_idx]
        key_right = key["bbox"]["x"] + key["bbox"]["width"]
        key_y = key["bbox"]["y"]
        key_h = key["bbox"]["height"]

        candidates: list[KIEWord] = []
        for w in words[key_idx + 1:]:
            if w["bbox"]["x"] > key_right - 5:
                y_overlap = (
                    min(key_y + key_h, w["bbox"]["y"] + w["bbox"]["height"])
                    - max(key_y, w["bbox"]["y"])
                )
                if y_overlap > key_h * 0.3:
                    candidates.append(w)
                    if len(candidates) >= 5:
                        break

        return candidates

    def _find_value_below(self, words: list[KIEWord], key_idx: int) -> list[KIEWord]:
        key = words[key_idx]
        key_x = key["bbox"]["x"]
        key_bottom = key["bbox"]["y"] + key["bbox"]["height"]
        key_w = key["bbox"]["width"]

        candidates: list[KIEWord] = []
        for w in words[key_idx + 1:]:
            if w["bbox"]["y"] > key_bottom - 5 and w["bbox"]["y"] < key_bottom + key["bbox"]["height"] * 3:
                x_overlap = (
                    min(key_x + key_w * 2, w["bbox"]["x"] + w["bbox"]["width"])
                    - max(key_x - key_w, w["bbox"]["x"])
                )
                if x_overlap > 0:
                    candidates.append(w)
                    if len(candidates) >= 5:
                        break

        return candidates
