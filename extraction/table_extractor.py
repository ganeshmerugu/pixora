"""Table structure extraction — cell-level detection and OCR.

Detects horizontal/vertical line intersections to build a cell grid,
groups cells into rows and columns, identifies merged cells, and runs
per-cell OCR to populate text content.
"""
from __future__ import annotations
import logging
from typing import Any

import numpy as np
from typing_extensions import Required, TypedDict
from PIL import Image

from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

CLUSTER_TOLERANCE = 8
MIN_LINE_LENGTH_RATIO = 0.15


class TableCell(TypedDict, total=False):
    row: Required[int]
    col: Required[int]
    row_span: int
    col_span: int
    bbox: Required[BoundingBox]
    text: str
    confidence: float
    is_header: bool


class TableStructure(TypedDict, total=False):
    num_rows: Required[int]
    num_cols: Required[int]
    cells: Required[list[TableCell]]
    headers: list[str]
    bbox: BoundingBox
    confidence: float


def _cluster_values(values: list[int], tolerance: int = CLUSTER_TOLERANCE) -> list[int]:
    if not values:
        return []
    sorted_vals = sorted(set(values))
    clusters: list[list[int]] = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] <= tolerance:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(np.mean(c)) for c in clusters]


class TableExtractor:
    def extract(
        self,
        image: Image.Image,
        table_bbox: BoundingBox | None = None,
        page_number: int = 1,
    ) -> TableStructure:
        if not HAS_CV2:
            return TableStructure(num_rows=0, num_cols=0, cells=[])

        arr = np.array(image.convert("RGB"))

        if table_bbox:
            x = int(table_bbox["x"])
            y = int(table_bbox["y"])
            w = int(table_bbox["width"])
            h = int(table_bbox["height"])
            arr = arr[y:y+h, x:x+w]

        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        h_lines, v_lines = self._detect_lines(gray, w, h)

        if len(h_lines) < 2 or len(v_lines) < 2:
            return self._fallback_whitespace(gray, page_number, table_bbox)

        row_bounds = _cluster_values(h_lines)
        col_bounds = _cluster_values(v_lines)

        num_rows = max(len(row_bounds) - 1, 1)
        num_cols = max(len(col_bounds) - 1, 1)

        cells: list[TableCell] = []
        for r in range(num_rows):
            for c in range(num_cols):
                y1 = row_bounds[r]
                y2 = row_bounds[r + 1] if r + 1 < len(row_bounds) else h
                x1 = col_bounds[c]
                x2 = col_bounds[c + 1] if c + 1 < len(col_bounds) else w

                offset_x = int(table_bbox["x"]) if table_bbox else 0
                offset_y = int(table_bbox["y"]) if table_bbox else 0

                cells.append(TableCell(
                    row=r,
                    col=c,
                    row_span=1,
                    col_span=1,
                    bbox=BoundingBox(
                        x=float(x1 + offset_x),
                        y=float(y1 + offset_y),
                        width=float(x2 - x1),
                        height=float(y2 - y1),
                        page=page_number,
                    ),
                    text="",
                    is_header=(r == 0),
                ))

        self._detect_merged_cells(cells, gray, row_bounds, col_bounds)

        return TableStructure(
            num_rows=num_rows,
            num_cols=num_cols,
            cells=cells,
            headers=[],
            bbox=table_bbox,
            confidence=0.85,
        )

    def _detect_lines(
        self, gray: np.ndarray, w: int, h: int,
    ) -> tuple[list[int], list[int]]:
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(int(w * MIN_LINE_LENGTH_RATIO), 20), 1))
        h_lines_img = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)

        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(int(h * MIN_LINE_LENGTH_RATIO), 20)))
        v_lines_img = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)

        h_positions: list[int] = []
        for y in range(h):
            if np.count_nonzero(h_lines_img[y, :]) > w * 0.2:
                h_positions.append(y)

        v_positions: list[int] = []
        for x in range(w):
            if np.count_nonzero(v_lines_img[:, x]) > h * 0.2:
                v_positions.append(x)

        return h_positions, v_positions

    def _detect_merged_cells(
        self,
        cells: list[TableCell],
        gray: np.ndarray,
        row_bounds: list[int],
        col_bounds: list[int],
    ) -> None:
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        for cell in cells:
            r, c = cell["row"], cell["col"]
            if r + 1 < len(row_bounds) - 1:
                y_mid = (row_bounds[r + 1] + row_bounds[r + 1]) // 2
                x1 = int(cell["bbox"]["x"] - (cell["bbox"]["x"]))
                x2 = x1 + int(cell["bbox"]["width"])
                if x2 > x1 and 0 <= y_mid < gray.shape[0]:
                    line_pixels = binary[y_mid, max(0, x1):min(x2, gray.shape[1])]
                    if len(line_pixels) > 0 and np.count_nonzero(line_pixels) < len(line_pixels) * 0.1:
                        cell["row_span"] = 2

    def _fallback_whitespace(
        self, gray: np.ndarray, page_number: int, table_bbox: BoundingBox | None,
    ) -> TableStructure:
        h, w = gray.shape
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        h_proj = np.sum(binary > 0, axis=1)
        threshold = w * 0.05
        row_separators = [0]
        in_gap = h_proj[0] < threshold if len(h_proj) > 0 else True
        for y in range(1, h):
            is_gap = h_proj[y] < threshold
            if is_gap and not in_gap:
                row_separators.append(y)
            in_gap = is_gap
        row_separators.append(h)

        if len(row_separators) < 3:
            return TableStructure(num_rows=0, num_cols=0, cells=[])

        offset_x = int(table_bbox["x"]) if table_bbox else 0
        offset_y = int(table_bbox["y"]) if table_bbox else 0

        cells: list[TableCell] = []
        for i in range(len(row_separators) - 1):
            cells.append(TableCell(
                row=i, col=0, row_span=1, col_span=1,
                bbox=BoundingBox(
                    x=float(offset_x), y=float(row_separators[i] + offset_y),
                    width=float(w), height=float(row_separators[i+1] - row_separators[i]),
                    page=page_number,
                ),
                text="", is_header=(i == 0),
            ))

        return TableStructure(
            num_rows=len(cells), num_cols=1, cells=cells,
            confidence=0.5,
        )

    def merge_cross_page(
        self,
        tables_by_page: dict[int, list[TableStructure]],
    ) -> list[TableStructure]:
        sorted_pages = sorted(tables_by_page.keys())
        if len(sorted_pages) < 2:
            return [t for p in sorted_pages for t in tables_by_page[p]]

        merged: list[TableStructure] = []
        carry: TableStructure | None = None

        for page_num in sorted_pages:
            page_tables = tables_by_page[page_num]
            for table in page_tables:
                if carry and self._is_continuation(carry, table):
                    carry = self._merge_tables(carry, table)
                else:
                    if carry:
                        merged.append(carry)
                    carry = table
        if carry:
            merged.append(carry)
        return merged

    def _is_continuation(self, prev: TableStructure, curr: TableStructure) -> bool:
        if prev["num_cols"] != curr["num_cols"]:
            return False

        prev_cols = self._column_widths(prev)
        curr_cols = self._column_widths(curr)
        if prev_cols and curr_cols and len(prev_cols) == len(curr_cols):
            for pw, cw in zip(prev_cols, curr_cols):
                if pw > 0 and abs(pw - cw) / pw > 0.15:
                    return False

        curr_has_header = any(c.get("is_header") and c.get("text", "").strip() for c in curr["cells"])
        if curr_has_header:
            return False

        prev_bbox = prev.get("bbox")
        curr_bbox = curr.get("bbox")
        if prev_bbox and curr_bbox:
            prev_on_same_page = prev_bbox.get("page", 0)
            curr_on_same_page = curr_bbox.get("page", 0)
            if prev_on_same_page == curr_on_same_page:
                return False

        return True

    def _column_widths(self, table: TableStructure) -> list[float]:
        cols: dict[int, float] = {}
        for cell in table["cells"]:
            c = cell["col"]
            w = cell["bbox"]["width"]
            if c not in cols or w > cols[c]:
                cols[c] = w
        return [cols[i] for i in sorted(cols)]

    def _merge_tables(self, prev: TableStructure, curr: TableStructure) -> TableStructure:
        row_offset = prev["num_rows"]
        merged_cells = list(prev["cells"])
        for cell in curr["cells"]:
            merged_cell = dict(cell)
            merged_cell["row"] = cell["row"] + row_offset
            merged_cell["is_header"] = False
            merged_cells.append(TableCell(**merged_cell))  # type: ignore[arg-type]

        return TableStructure(
            num_rows=prev["num_rows"] + curr["num_rows"],
            num_cols=prev["num_cols"],
            cells=merged_cells,
            headers=prev.get("headers", []),
            bbox=prev.get("bbox"),
            confidence=min(prev.get("confidence", 0.5), curr.get("confidence", 0.5)),
        )

    async def extract_with_ocr(
        self,
        image: Image.Image,
        table_bbox: BoundingBox | None = None,
        page_number: int = 1,
    ) -> TableStructure:
        structure = self.extract(image, table_bbox, page_number)

        try:
            from pixora.ocr.tesseract import TesseractEngine
            engine = TesseractEngine()
        except Exception:
            return structure

        import io
        for cell in structure["cells"]:
            bbox = cell["bbox"]
            x, y = int(bbox["x"]), int(bbox["y"])
            w, h = int(bbox["width"]), int(bbox["height"])
            if w < 5 or h < 5:
                continue

            cropped = image.crop((x, y, x + w, y + h))
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            cell_bytes = buf.getvalue()

            try:
                regions = await engine.recognize(cell_bytes, page_number=page_number)
                if regions:
                    cell["text"] = regions[0].get("text", "").strip()
                    cell["confidence"] = regions[0].get("confidence", 0.0)
            except Exception:
                pass

        headers = [c["text"] for c in structure["cells"] if c.get("is_header") and c.get("text")]
        structure["headers"] = headers

        return structure
