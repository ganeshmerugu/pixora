from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class ValidationRule(TypedDict, total=False):
    type: Required[str]
    params: Required[dict[str, Any]]
    message: str


class OntologyNode(TypedDict, total=False):
    name: Required[str]
    field_type: Required[str]
    description: str
    aliases: list[str]
    validation_rules: list[ValidationRule]
    parent: str
    required: bool
    metadata: dict[str, Any]


class ExtractionSchema(TypedDict, total=False):
    schema_id: Required[str]
    doc_type: Required[str]
    version: Required[str]
    nodes: Required[list[OntologyNode]]
    metadata: dict[str, Any]
