from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class BoundingBox(TypedDict, total=False):
    x: Required[float]
    y: Required[float]
    width: Required[float]
    height: Required[float]
    page: int


class Region(TypedDict, total=False):
    id: Required[str]
    type: Required[str]
    content: Required[str]
    bbox: BoundingBox
    confidence: float
    children: list["Region"]
    reading_order: int
    metadata: dict[str, Any]


class Page(TypedDict, total=False):
    page_number: Required[int]
    regions: Required[list[Region]]
    width: float
    height: float
    metadata: dict[str, Any]


class DocumentTree(TypedDict, total=False):
    document_id: Required[str]
    pages: Required[list[Page]]
    source_format: str
    text_layer_present: bool
    metadata: dict[str, Any]
