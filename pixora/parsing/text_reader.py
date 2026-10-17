from __future__ import annotations
import uuid
from pixora.parsing.reader import BaseReader
from pixora.models.document import DocumentTree, Page, Region


class TextReader(BaseReader):
    supported_formats = [".txt", ".text", ".log", ".md", ".markdown", ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".rtf"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        text = file_bytes.decode("utf-8", errors="replace")
        return DocumentTree(
            document_id=uuid.uuid4().hex,
            pages=[Page(
                page_number=1,
                regions=[Region(
                    id=f"r_text_{uuid.uuid4().hex[:8]}",
                    type="TEXT",
                    content=text,
                    confidence=1.0,
                )],
            )],
            source_format="text",
            text_layer_present=True,
        )
