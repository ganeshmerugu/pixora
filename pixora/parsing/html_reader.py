from __future__ import annotations
import uuid
from bs4 import BeautifulSoup
from pixora.parsing.reader import BaseReader
from pixora.models.document import DocumentTree, Page, Region


class HTMLReader(BaseReader):
    supported_formats = [".html", ".htm"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        soup = BeautifulSoup(file_bytes, "html.parser")
        regions: list[Region] = []
        for i, elem in enumerate(soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "table", "li"])):
            text = elem.get_text(strip=True)
            if not text:
                continue
            rtype = "HEADER" if elem.name.startswith("h") else "TABLE" if elem.name == "table" else "TEXT"
            regions.append(Region(
                id=f"r_html_{i}_{uuid.uuid4().hex[:8]}",
                type=rtype,
                content=text,
                confidence=1.0,
            ))
        return DocumentTree(
            document_id=uuid.uuid4().hex,
            pages=[Page(page_number=1, regions=regions)],
            source_format="html",
            text_layer_present=True,
        )
