from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pixora.api.models import QualityResponse, GroundingResponse
from pixora.storage import get_job

router = APIRouter(tags=["quality"])

_quality_store: dict[str, dict] = {}
_grounding_store: dict[str, dict] = {}
_trace_store: dict[str, dict] = {}
_cost_store: dict[str, dict] = {}


def _get_from_db(job_id: str, field: str) -> dict | None:
    job = get_job(job_id)
    if job and job.get(field):
        return job[field]
    return None


def store_quality(job_id: str, report: dict) -> None:
    _quality_store[job_id] = report


def store_grounding(job_id: str, report: dict) -> None:
    _grounding_store[job_id] = report


def store_trace(job_id: str, trace: dict) -> None:
    _trace_store[job_id] = trace


def store_cost(job_id: str, report: dict) -> None:
    _cost_store[job_id] = report


@router.get("/parse/{job_id}/quality", response_model=QualityResponse)
async def get_quality(job_id: str):
    report = _quality_store.get(job_id) or _get_from_db(job_id, "quality_report")
    if not report:
        raise HTTPException(status_code=404, detail="Quality report not found")
    return QualityResponse(
        document_id=report.get("document_id", ""),
        overall_score=report.get("overall_score", 0.0),
        completeness=report.get("completeness"),
        grounding_score=report.get("grounding_score"),
        recommendation=report.get("recommendation"),
        issues=report.get("issues", []),
    )


@router.get("/parse/{job_id}/grounding", response_model=GroundingResponse)
async def get_grounding(job_id: str):
    report = _grounding_store.get(job_id) or _get_from_db(job_id, "grounding_report")
    if not report:
        raise HTTPException(status_code=404, detail="Grounding report not found")
    return GroundingResponse(
        document_id=report.get("document_id", ""),
        grounding_rate=report.get("grounding_rate", 0.0),
        grounded_count=report.get("grounded_count", 0),
        ungrounded_count=report.get("ungrounded_count", 0),
        flagged_hallucinations=report.get("flagged_hallucinations", []),
    )


@router.get("/parse/{job_id}/trace")
async def get_trace(job_id: str):
    trace = _trace_store.get(job_id) or _get_from_db(job_id, "trace")
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/parse/{job_id}/cost")
async def get_cost(job_id: str):
    report = _cost_store.get(job_id) or _get_from_db(job_id, "cost_report")
    if not report:
        raise HTTPException(status_code=404, detail="Cost report not found")
    return report
