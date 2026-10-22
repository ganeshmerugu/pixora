from __future__ import annotations
import pytest
from pixora.parsing.reader import BaseReader, ReaderRegistry
from pixora.models.document import DocumentTree


class FakeReader(BaseReader):
    supported_formats = [".fake"]

    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree:
        return DocumentTree(document_id="test", pages=[])


def test_base_reader_interface():
    reader = FakeReader()
    assert ".fake" in reader.supported_formats


def test_reader_registry_register_and_get():
    registry = ReaderRegistry()
    registry.register(FakeReader())
    reader = registry.get_reader("test.fake")
    assert isinstance(reader, FakeReader)


def test_reader_registry_unknown_format():
    registry = ReaderRegistry()
    with pytest.raises(KeyError):
        registry.get_reader("test.xyz")


def test_reader_registry_pdf():
    registry = ReaderRegistry()
    from pixora.parsing.pdf_reader import PDFReader
    registry.register(PDFReader())
    reader = registry.get_reader("document.pdf")
    assert reader.supported_formats == [".pdf"]


def test_reader_registry_image_formats():
    registry = ReaderRegistry()
    from pixora.parsing.image_reader import ImageReader
    registry.register(ImageReader())
    for ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]:
        reader = registry.get_reader(f"photo{ext}")
        assert isinstance(reader, ImageReader)
