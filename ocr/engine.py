from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.models.document import BoundingBox


class RecognizedWord(TypedDict, total=False):
    text: Required[str]
    confidence: Required[float]
    bbox: Required[BoundingBox]
    alternatives: list[str]


class RecognizedRegion(TypedDict, total=False):
    region_id: Required[str]
    text: Required[str]
    confidence: Required[float]
    words: list[RecognizedWord]
    engine: str
    metadata: dict[str, Any]


class OCREngine(ABC):
    engine_name: str = ""

    @abstractmethod
    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]: ...
