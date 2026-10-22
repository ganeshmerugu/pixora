from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from PIL import Image
import numpy as np
from pixora.models.document import BoundingBox

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class DetectedZone(TypedDict, total=False):
    zone_id: Required[str]
    zone_type: Required[str]
    bbox: Required[BoundingBox]
    confidence: float
    metadata: dict[str, Any]


class LayoutAnalysis(TypedDict, total=False):
    zones: Required[list[DetectedZone]]
    page_number: int
    estimated_columns: int
    has_header: bool
    has_footer: bool
    has_tables: bool
    metadata: dict[str, Any]


HEADER_ZONE_FRACTION = 0.12
FOOTER_ZONE_FRACTION = 0.10
TABLE_LINE_THRESHOLD = 5
MIN_ZONE_AREA_FRACTION = 0.005


class LayoutZoneDetector:
    def detect(self, image: Image.Image, page_number: int = 1) -> LayoutAnalysis:
        if not HAS_CV2:
            return self._fallback_detect(image, page_number)

        arr = np.array(image.convert("RGB"))
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        zones: list[DetectedZone] = []
        zone_idx = 0

        header_zone, zone_idx = self._detect_header(gray, w, h, page_number, zone_idx)
        if header_zone:
            zones.append(header_zone)

        footer_zone, zone_idx = self._detect_footer(gray, w, h, page_number, zone_idx)
        if footer_zone:
            zones.append(footer_zone)

        table_zones, zone_idx = self._detect_tables(gray, w, h, page_number, zone_idx)
        zones.extend(table_zones)

        text_zones, zone_idx = self._detect_text_blocks(gray, w, h, page_number, zone_idx, zones)
        zones.extend(text_zones)

        columns = self._estimate_columns(zones, w)

        return LayoutAnalysis(
            zones=zones,
            page_number=page_number,
            estimated_columns=columns,
            has_header=header_zone is not None,
            has_footer=footer_zone is not None,
            has_tables=len(table_zones) > 0,
        )

    def _detect_header(self, gray: np.ndarray, w: int, h: int, page: int, idx: int) -> tuple[DetectedZone | None, int]:
        header_h = int(h * HEADER_ZONE_FRACTION)
        region = gray[:header_h, :]
        if np.mean(region) < 250:
            return DetectedZone(
                zone_id=f"zone_{page}_{idx}",
                zone_type="HEADER",
                bbox=BoundingBox(x=0, y=0, width=float(w), height=float(header_h), page=page),
                confidence=0.7,
            ), idx + 1
        return None, idx

    def _detect_footer(self, gray: np.ndarray, w: int, h: int, page: int, idx: int) -> tuple[DetectedZone | None, int]:
        footer_start = int(h * (1 - FOOTER_ZONE_FRACTION))
        region = gray[footer_start:, :]
        if np.mean(region) < 250:
            return DetectedZone(
                zone_id=f"zone_{page}_{idx}",
                zone_type="FOOTER",
                bbox=BoundingBox(x=0, y=float(footer_start), width=float(w), height=float(h - footer_start), page=page),
                confidence=0.7,
            ), idx + 1
        return None, idx

    def _detect_tables(self, gray: np.ndarray, w: int, h: int, page: int, idx: int) -> tuple[list[DetectedZone], int]:
        tables: list[DetectedZone] = []
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 8, 1), 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        h_count = cv2.countNonZero(horizontal_lines)

        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 8, 1)))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        v_count = cv2.countNonZero(vertical_lines)

        if h_count > 100 and v_count > 100:
            combined = cv2.add(horizontal_lines, vertical_lines)
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_area = w * h * MIN_ZONE_AREA_FRACTION

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    x, y, cw, ch = cv2.boundingRect(contour)
                    tables.append(DetectedZone(
                        zone_id=f"zone_{page}_{idx}",
                        zone_type="TABLE",
                        bbox=BoundingBox(x=float(x), y=float(y), width=float(cw), height=float(ch), page=page),
                        confidence=0.8,
                    ))
                    idx += 1

        return tables, idx

    def _detect_text_blocks(
        self, gray: np.ndarray, w: int, h: int, page: int, idx: int, existing: list[DetectedZone]
    ) -> tuple[list[DetectedZone], int]:
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 20, 5), 5))
        dilated = cv2.dilate(binary, kernel, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        blocks: list[DetectedZone] = []
        min_area = w * h * MIN_ZONE_AREA_FRACTION

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            x, y, cw, ch = cv2.boundingRect(contour)
            if self._overlaps_existing(x, y, cw, ch, existing):
                continue

            blocks.append(DetectedZone(
                zone_id=f"zone_{page}_{idx}",
                zone_type="TEXT",
                bbox=BoundingBox(x=float(x), y=float(y), width=float(cw), height=float(ch), page=page),
                confidence=0.75,
            ))
            idx += 1

        return blocks, idx

    def _overlaps_existing(self, x: int, y: int, w: int, h: int, existing: list[DetectedZone]) -> bool:
        for zone in existing:
            zb = zone["bbox"]
            zx, zy = zb["x"], zb["y"]
            zw, zh = zb["width"], zb["height"]
            overlap_x = max(0, min(x + w, zx + zw) - max(x, zx))
            overlap_y = max(0, min(y + h, zy + zh) - max(y, zy))
            overlap_area = overlap_x * overlap_y
            if overlap_area > 0.5 * w * h:
                return True
        return False

    def _estimate_columns(self, zones: list[DetectedZone], page_width: int) -> int:
        text_zones = [z for z in zones if z["zone_type"] == "TEXT"]
        if len(text_zones) < 2:
            return 1

        x_centers = sorted([z["bbox"]["x"] + z["bbox"]["width"] / 2 for z in text_zones])
        if len(x_centers) < 2:
            return 1

        gaps = [x_centers[i+1] - x_centers[i] for i in range(len(x_centers) - 1)]
        significant_gaps = [g for g in gaps if g > page_width * 0.15]

        return len(significant_gaps) + 1

    def enrich_semantics(
        self,
        zones: list[DetectedZone],
        ocr_words: list[dict],
    ) -> list[DetectedZone]:
        if not ocr_words:
            return zones

        body_sizes = [w.get("font_size", 0) for w in ocr_words if w.get("font_size", 0) > 0]
        median_size = sorted(body_sizes)[len(body_sizes) // 2] if body_sizes else 12.0

        for zone in zones:
            if zone["zone_type"] not in ("TEXT",):
                continue

            words_in_zone = self._words_in_bbox(ocr_words, zone["bbox"])
            if not words_in_zone:
                continue

            if self._is_heading(words_in_zone, median_size):
                zone["zone_type"] = "HEADING"
                zone.setdefault("metadata", {})["semantic_type"] = "heading"
                continue

            if self._is_list(words_in_zone):
                zone["zone_type"] = "LIST"
                zone.setdefault("metadata", {})["semantic_type"] = "list"
                continue

        for i, zone in enumerate(zones):
            if zone["zone_type"] in ("TEXT",):
                prev_types = [zones[j]["zone_type"] for j in range(max(0, i - 1), i)]
                if any(t in ("TABLE", "FIGURE") for t in prev_types):
                    words_in_zone = self._words_in_bbox(ocr_words, zone["bbox"])
                    if words_in_zone and len(words_in_zone) <= 20:
                        avg_size = sum(w.get("font_size", median_size) for w in words_in_zone) / len(words_in_zone)
                        if avg_size < median_size * 0.9:
                            zone["zone_type"] = "CAPTION"
                            zone.setdefault("metadata", {})["semantic_type"] = "caption"

        return zones

    def _words_in_bbox(self, words: list[dict], bbox: BoundingBox) -> list[dict]:
        result = []
        bx = bbox["x"]
        by = bbox["y"]
        bx2 = bx + bbox["width"]
        by2 = by + bbox["height"]
        for w in words:
            wb = w.get("bbox", {})
            wx = wb.get("x", 0)
            wy = wb.get("y", 0)
            if bx <= wx <= bx2 and by <= wy <= by2:
                result.append(w)
        return result

    def _is_heading(self, words: list[dict], median_size: float) -> bool:
        if not words:
            return False
        sizes = [w.get("font_size", 0) for w in words if w.get("font_size", 0) > 0]
        if not sizes:
            bolds = [w for w in words if w.get("bold")]
            text = " ".join(w.get("text", "") for w in words)
            return len(bolds) > len(words) * 0.5 and len(text) < 100

        avg_size = sum(sizes) / len(sizes)
        text = " ".join(w.get("text", "") for w in words)
        lines = text.count("\n") + 1
        return avg_size > median_size * 1.2 and lines <= 3

    def _is_list(self, words: list[dict]) -> bool:
        if len(words) < 3:
            return False
        texts = [w.get("text", "") for w in words]
        bullet_count = 0
        for t in texts:
            stripped = t.strip()
            if stripped and (stripped[0] in "•·-–—◦▪►" or (len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] in ".)")):
                bullet_count += 1
        return bullet_count >= 2

    def _fallback_detect(self, image: Image.Image, page_number: int) -> LayoutAnalysis:
        w, h = image.size
        return LayoutAnalysis(
            zones=[DetectedZone(
                zone_id=f"zone_{page_number}_0",
                zone_type="TEXT",
                bbox=BoundingBox(x=0, y=0, width=float(w), height=float(h), page=page_number),
                confidence=0.5,
            )],
            page_number=page_number,
            estimated_columns=1,
            has_header=False,
            has_footer=False,
            has_tables=False,
        )
