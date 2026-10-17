from __future__ import annotations
import os
from abc import ABC, abstractmethod
from pixora.models.document import DocumentTree


class BaseReader(ABC):
    supported_formats: list[str] = []

    @abstractmethod
    async def read(self, file_bytes: bytes, filename: str) -> DocumentTree: ...


class ReaderRegistry:
    def __init__(self) -> None:
        self._readers: dict[str, BaseReader] = {}

    def register(self, reader: BaseReader) -> None:
        for fmt in reader.supported_formats:
            self._readers[fmt.lower()] = reader

    def get_reader(self, filename: str) -> BaseReader:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self._readers:
            raise KeyError(f"No reader for format: {ext}")
        return self._readers[ext]
