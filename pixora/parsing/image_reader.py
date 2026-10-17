from __future__ import annotations
import uuid
from pixora.parsing.reader import BaseReader
from pixora.models.document import DocumentTree, Page, Region


class ImageReader(BaseReader):
    supported_formats = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".heic", ".heif", ".avif", ".svg", ".gif", ".ico"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        return DocumentTree(
            document_id=uuid.uuid4().hex,
            pages=[Page(
                page_number=1,
                regions=[Region(id=f"r_img_{uuid.uuid4().hex[:8]}", type="IMAGE", content="", metadata={"needs_ocr": True})],
            )],
            source_format="image",
            text_layer_present=False,
        )
