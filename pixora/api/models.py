from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any


class ParseRequest(BaseModel):
    file_id: str
    tier: str = "agentic"
    extraction_target: str = "per_doc"
    expand: list[str] = Field(default_factory=lambda: ["markdown"])
    extraction_schema: dict[str, Any] | None = None
    processing_options: dict[str, Any] | None = None
    webhook_url: str | None = None
    split_documents: bool = False
    source_url: str | None = None


class ExtractRequest(BaseModel):
    file_id: str
    data_schema: dict[str, Any]
    tier: str = "agentic"


class ClassifyRequest(BaseModel):
    file_id: str
    rules: list[dict[str, str]]
    mode: str = "FAST"


class JobResponse(BaseModel):
    job_id: str
    status: str
    document_id: str | None = None
    result: dict[str, Any] | None = None


class QualityResponse(BaseModel):
    document_id: str
    overall_score: float
    completeness: float | None = None
    grounding_score: float | None = None
    recommendation: str | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)


class GroundingResponse(BaseModel):
    document_id: str
    grounding_rate: float
    grounded_count: int
    ungrounded_count: int
    flagged_hallucinations: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
