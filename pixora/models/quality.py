from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class QualityIssue(TypedDict, total=False):
    severity: Required[str]
    dimension: Required[str]
    message: Required[str]
    field: str
    region_id: str


class FieldConfidence(TypedDict, total=False):
    field: Required[str]
    parsing_confidence: Required[float]
    extraction_confidence: Required[float]
    overall: Required[float]


class ParseQualityReport(TypedDict, total=False):
    document_id: Required[str]
    overall_score: Required[float]
    completeness: float
    accuracy_confidence: float
    grounding_score: float
    layout_fidelity: float
    extraction_cost: float
    processing_time_ms: int
    issues: list[QualityIssue]
    recommendation: str
    field_confidences: list[FieldConfidence]
    metadata: dict[str, Any]
