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


VALID_FIELD_TYPES = {
    "STRING", "NUMBER", "DATE", "CURRENCY", "BOOLEAN", "ENUM",
    "EMAIL", "PHONE", "URL", "ADDRESS", "LIST", "TABLE",
}


def validate_schema(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_id", "doc_type", "version", "nodes"):
        if key not in schema:
            errors.append(f"Missing required field: {key}")
    nodes = schema.get("nodes")
    if not isinstance(nodes, list):
        errors.append("'nodes' must be a list")
        return errors
    if len(nodes) == 0:
        errors.append("Schema must have at least one node")
    seen_names: set[str] = set()
    for i, node in enumerate(nodes):
        name = node.get("name", "")
        if not name:
            errors.append(f"Node {i}: missing 'name'")
        elif name in seen_names:
            errors.append(f"Duplicate node name: '{name}'")
        else:
            seen_names.add(name)
        ft = node.get("field_type", "")
        if not ft:
            errors.append(f"Node '{name}': missing 'field_type'")
        elif ft not in VALID_FIELD_TYPES:
            errors.append(f"Node '{name}': invalid field_type '{ft}', must be one of {sorted(VALID_FIELD_TYPES)}")
        for rule in node.get("validation_rules", []):
            if "type" not in rule or "params" not in rule:
                errors.append(f"Node '{name}': validation rule missing 'type' or 'params'")
    return errors
