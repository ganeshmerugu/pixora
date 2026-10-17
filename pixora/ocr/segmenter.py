from __future__ import annotations
import logging
import uuid
from typing import Any
from typing_extensions import Required, TypedDict
from PIL import Image
import numpy as np
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class SegmentedWord(TypedDict, total=False):
    bbox: Required[BoundingBox]
    characters: list[BoundingBox]


class SegmentedLine(TypedDict, total=False):
    bbox: Required[BoundingBox]
    words: list[SegmentedWord]
    baseline: float


class SegmentedRegion(TypedDict, total=False):
    id: Required[str]
    type: Required[str]
    bbox: Required[BoundingBox]
    lines: list[SegmentedLine]
    confidence: float
    metadata: dict[str, Any]


class SegmentationResult(TypedDict, total=False):
    regions: Required[list[SegmentedRegion]]
    page_dimensions: tuple[int, int]
    metadata: dict[str, Any]


HEADER_FRACTION = 0.12
FOOTER_FRACTION = 0.10
MIN_REGION_AREA_RATIO = 0.002


class TextSegmenter:
    def segment(self, image: Image.Image, page_number: int = 1) -> SegmentationResult:
        width, height = image.size

        if not HAS_CV2 or width < 50 or height < 50:
            return self._single_region_fallback(width, height, page_number)

        try:
            arr = np.array(image.convert("RGB"))
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        except Exception:
            return self._single_region_fallback(width, height, page_number)

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 8))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return self._single_region_fallback(width, height, page_number)

        min_area = width * height * MIN_REGION_AREA_RATIO
        regions: list[SegmentedRegion] = []
        idx = 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < min_area:
                continue

            region_type = self._classify_region(x, y, w, h, width, height)

            regions.append(SegmentedRegion(
                id=f"seg_p{page_number}_r{idx}",
                type=region_type,
                bbox=BoundingBox(
                    x=float(x), y=float(y),
                    width=float(w), height=float(h),
                    page=page_number,
                ),
                lines=[],
                confidence=0.85,
            ))
            idx += 1

        regions.sort(key=lambda r: (r["bbox"]["y"], r["bbox"]["x"]))

        if not regions:
            return self._single_region_fallback(width, height, page_number)

        return SegmentationResult(
            regions=regions,
            page_dimensions=(width, height),
            metadata={"method": "morphological", "contours_found": len(contours)},
        )

    def _classify_region(
        self, x: int, y: int, w: int, h: int, page_w: int, page_h: int,
    ) -> str:
        y_center = y + h / 2
        if y_center < page_h * HEADER_FRACTION:
            return "HEADER"
        if y_center > page_h * (1 - FOOTER_FRACTION):
            return "FOOTER"
        aspect = w / max(h, 1)
        if aspect > 5 and h < page_h * 0.05:
            return "HEADER"
        if w > page_w * 0.8 and h > page_h * 0.15:
            return "TABLE"
        return "TEXT"

    def _single_region_fallback(
        self, width: int, height: int, page_number: int,
    ) -> SegmentationResult:
        return SegmentationResult(
            regions=[SegmentedRegion(
                id=f"seg_p{page_number}_r0",
                type="TEXT",
                bbox=BoundingBox(x=0, y=0, width=float(width), height=float(height), page=page_number),
                lines=[],
                confidence=0.7,
            )],
            page_dimensions=(width, height),
            metadata={"method": "fallback"},
        )

    def segment_with_tesseract_data(
        self, tsv_data: list[dict], page_number: int = 1,
        page_width: float = 0, page_height: float = 0,
    ) -> SegmentationResult:
        current_lines: dict[int, list[dict]] = {}

        for entry in tsv_data:
            level = int(entry.get("level", 0))
            if level == 5:
                line_num = int(entry.get("line_num", 0))
                current_lines.setdefault(line_num, []).append(entry)

        lines: list[SegmentedLine] = []
        for line_num in sorted(current_lines.keys()):
            words_data = current_lines[line_num]
            words: list[SegmentedWord] = []
            for w in words_data:
                x, y = float(w.get("left", 0)), float(w.get("top", 0))
                w_width, w_height = float(w.get("width", 0)), float(w.get("height", 0))
                words.append(SegmentedWord(
                    bbox=BoundingBox(x=x, y=y, width=w_width, height=w_height, page=page_number),
                ))
            if words:
                first = words[0]["bbox"]
                last = words[-1]["bbox"]
                line_bbox = BoundingBox(
                    x=first["x"], y=first["y"],
                    width=last["x"] + last["width"] - first["x"],
                    height=max(w["bbox"]["height"] for w in words),
                    page=page_number,
                )
                lines.append(SegmentedLine(bbox=line_bbox, words=words))

        regions: list[SegmentedRegion] = []
        if lines:
            first_line = lines[0]["bbox"]
            last_line = lines[-1]["bbox"]
            region_bbox = BoundingBox(
                x=first_line["x"], y=first_line["y"],
                width=max(l["bbox"]["width"] for l in lines),
                height=last_line["y"] + last_line["height"] - first_line["y"],
                page=page_number,
            )
            regions.append(SegmentedRegion(
                id=f"seg_p{page_number}_r0",
                type="TEXT",
                bbox=region_bbox,
                lines=lines,
                confidence=0.9,
            ))

        return SegmentationResult(
            regions=regions,
            page_dimensions=(int(page_width), int(page_height)),
            metadata={"method": "tesseract_data"},
        )
