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
