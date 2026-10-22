from __future__ import annotations
import logging
import uuid
import io
from pixora.parsing.reader import BaseReader
from pixora.models.document import DocumentTree, Page, Region, BoundingBox

logger = logging.getLogger(__name__)


class PDFReader(BaseReader):
    supported_formats = [".pdf"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        try:
            return self._read_pdfplumber(file_bytes)
        except Exception as e:
            logger.debug("pdfplumber failed: %s", e)

        try:
            return self._read_pymupdf(file_bytes)
        except Exception as e:
            logger.debug("pymupdf failed: %s", e)

        raise ValueError("Could not parse PDF with any available backend")

    def _read_pdfplumber(self, file_bytes: bytes) -> DocumentTree:
        import pdfplumber
        pages: list[Page] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, pg in enumerate(pdf.pages):
                regions: list[Region] = []

                try:
                    text = pg.extract_text(layout=True, x_density=7.25, y_density=13.8) or ""
                except TypeError:
                    text = pg.extract_text() or ""

                if text.strip():
                    regions.append(Region(
                        id=f"r_{i}_text_{uuid.uuid4().hex[:8]}",
                        type="TEXT",
                        content=text,
                        bbox=BoundingBox(x=0, y=0, width=float(pg.width), height=float(pg.height), page=i + 1),
                        confidence=1.0,
                        reading_order=0,
                    ))

                for t_idx, table in enumerate(pg.extract_tables() or []):
                    if not table:
                        continue
                    md_lines = _table_to_markdown(table)
                    if md_lines:
                        regions.append(Region(
                            id=f"r_{i}_table_{t_idx}_{uuid.uuid4().hex[:8]}",
                            type="TABLE",
                            content=md_lines,
                            confidence=0.9,
                            reading_order=t_idx + 1,
                        ))

                pages.append(Page(page_number=i + 1, regions=regions, width=float(pg.width), height=float(pg.height)))

        return DocumentTree(
            document_id=uuid.uuid4().hex, pages=pages, source_format="pdf",
            text_layer_present=any(r["type"] == "TEXT" for p in pages for r in p["regions"]),
        )

    def _read_pymupdf(self, file_bytes: bytes) -> DocumentTree:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[Page] = []
        try:
            for i, pg in enumerate(doc):
                regions: list[Region] = []

                blocks = pg.get_text("dict", sort=True).get("blocks", [])
                text_parts: list[tuple[float, float, str]] = []
                for block in blocks:
                    if block.get("type") == 0:
                        y = block.get("bbox", [0, 0, 0, 0])[1]
                        x = block.get("bbox", [0, 0, 0, 0])[0]
                        lines_text = []
                        for line in block.get("lines", []):
                            spans_text = "".join(span.get("text", "") for span in line.get("spans", []))
                            if spans_text.strip():
                                lines_text.append(spans_text)
                        if lines_text:
                            text_parts.append((y, x, "\n".join(lines_text)))

                text_parts.sort(key=lambda t: (t[0], t[1]))
                full_text = "\n\n".join(t[2] for t in text_parts)

                if full_text.strip():
                    rect = pg.rect
                    regions.append(Region(
                        id=f"r_{i}_fitz_{uuid.uuid4().hex[:8]}",
                        type="TEXT",
                        content=full_text,
                        bbox=BoundingBox(x=0, y=0, width=float(rect.width), height=float(rect.height), page=i + 1),
                        confidence=1.0,
                        reading_order=0,
                    ))

                pages.append(Page(page_number=i + 1, regions=regions, width=float(pg.rect.width), height=float(pg.rect.height)))
        finally:
            doc.close()

        return DocumentTree(
            document_id=uuid.uuid4().hex, pages=pages, source_format="pdf",
            text_layer_present=any(r["type"] == "TEXT" for p in pages for r in p["regions"]),
        )


def _table_to_markdown(table: list[list]) -> str:
    if not table or not table[0]:
        return ""

    header = table[0]
    cols = len(header)
    md_header = "| " + " | ".join(str(c or "").strip() for c in header) + " |"
    md_sep = "| " + " | ".join("---" for _ in range(cols)) + " |"
    md_rows = []
    for row in table[1:]:
        if not row:
            continue
        cells = [(str(c or "").strip()) for c in row]
        while len(cells) < cols:
            cells.append("")
        md_rows.append("| " + " | ".join(cells[:cols]) + " |")

    if not md_rows:
        return md_header

    return "\n".join([md_header, md_sep] + md_rows)
