from __future__ import annotations
import uuid
import io
from docx import Document
from pixora.parsing.reader import BaseReader
from pixora.models.document import DocumentTree, Page, Region


class DocxReader(BaseReader):
    supported_formats = [".docx", ".doc"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        doc = Document(io.BytesIO(file_bytes))
        regions: list[Region] = []
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                regions.append(Region(
                    id=f"r_docx_{i}_{uuid.uuid4().hex[:8]}",
                    type="HEADER" if para.style and "heading" in (para.style.name or "").lower() else "TEXT",
                    content=para.text,
                    confidence=1.0,
                ))
        for t_idx, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append(" | ".join(cell.text for cell in row.cells))
            regions.append(Region(
                id=f"r_docx_table_{t_idx}_{uuid.uuid4().hex[:8]}",
                type="TABLE",
                content="\n".join(rows),
                confidence=1.0,
            ))
        return DocumentTree(
            document_id=uuid.uuid4().hex,
            pages=[Page(page_number=1, regions=regions)],
            source_format="docx",
            text_layer_present=True,
        )
