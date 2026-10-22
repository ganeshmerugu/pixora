from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class DocumentProfile(TypedDict, total=False):
    doc_type: Required[str]
    confidence: Required[float]
    complexity: float
    languages: list[str]
    has_tables: bool
    has_handwriting: bool
    has_images: bool
    is_scanned: bool
    text_layer_present: bool
    page_count: int
    recommended_strategy: str
    metadata: dict[str, Any]


class ProcessingPlan(TypedDict, total=False):
    ocr_strategy: Required[str]
    extraction_mode: Required[str]
    max_correction_rounds: int
    target_quality: float
    deskew: bool
    denoise: bool
    enhance_contrast: bool
    chunk_size: int
    overlap: int
    confidence_threshold: float
    metadata: dict[str, Any]


class CorrectionDelta(TypedDict, total=False):
    round_number: Required[int]
    issues_found: Required[list[str]]
    corrections_applied: list[str]
    fields_updated: list[str]
    score_before: float
    score_after: float
    metadata: dict[str, Any]


class PipelineState(TypedDict, total=False):
    document_id: Required[str]
    job_id: Required[str]
    raw_bytes: bytes
    source_filename: str
    profile: DocumentProfile
    processing_plan: ProcessingPlan
    document_tree: Any
    extraction_schema: Any
    extraction_result: dict[str, Any]
    quality_report: Any
    current_stage: str
    correction_rounds: int
    correction_round: CorrectionDelta
    cost_tracker: dict[str, Any]
    decision_trace: list[dict[str, Any]]
    task_hypotheses: list[dict[str, Any]]
    failure_attributions: list[dict[str, Any]]
    context_trace: list[dict[str, Any]]
    verification_report: dict[str, Any]
    validator_issues: list[dict[str, Any]]
    metadata: dict[str, Any]
