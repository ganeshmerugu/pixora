from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.models.pipeline import DocumentProfile, ProcessingPlan, CorrectionDelta


class AgentState(TypedDict, total=False):
    document_id: Required[str]
    job_id: Required[str]
    raw_bytes: bytes
    source_filename: str

    # Classifier output
    profile: DocumentProfile

    # Router output
    processing_plan: ProcessingPlan

    # Reader output
    document_tree: dict[str, Any]

    # Extractor I/O
    extraction_schema: dict[str, Any]
    extraction_result: dict[str, Any]

    # Validator output
    validator_issues: list[dict[str, Any]]
    validation_passed: bool

    # Scorer output
    quality_report: dict[str, Any]
    quality_score: float

    # Self-correction loop
    correction_round: int
    correction_rounds: list[CorrectionDelta]
    max_correction_rounds: int

    # Harness traces (C5, C7, C8)
    task_hypotheses: list[dict]
    failure_attributions: list[dict]
    context_trace: dict
    verification_report: dict

    # Cost tracking
    cost_tracker: dict[str, Any]
    decision_trace: list[dict[str, Any]]

    # Terminal state
    recommendation: str
    metadata: dict[str, Any]
