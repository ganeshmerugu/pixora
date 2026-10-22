from __future__ import annotations
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

router = APIRouter(prefix="/evals", tags=["evals"])

_reports: dict[str, dict] = {}
_drift_reports: list[dict] = []


class RunRequest(BaseModel):
    suite_name: str = "default"
    benchmark_ids: list[str] = Field(default_factory=list)


class ReportResponse(BaseModel):
    id: str
    suite_name: str
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    avg_f1: float = 0.0
    avg_quality: float = 0.0
    status: str = "completed"
    by_doc_type: dict[str, Any] = Field(default_factory=dict)
    failures: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/run")
async def run_suite(request: RunRequest):
    try:
        from pixora.pipeline_runner import run_all_benchmarks
        stats = await run_all_benchmarks()
        d = stats.to_dict()
    except Exception as e:
        return {"id": "error", "suite_name": request.suite_name, "error": str(e), "total_cases": 0, "passed": 0, "failed": 0, "pass_rate": 0, "avg_f1": 0, "avg_quality": 0, "status": "failed"}

    passed = int(d.get("pass_rate", 0) * d.get("total_documents", 0))
    failed = d.get("total_documents", 0) - passed

    report_id = uuid.uuid4().hex[:16]
    data = {
        "id": report_id,
        "suite_name": request.suite_name,
        "total_cases": d.get("total_documents", 0),
        "passed": passed,
        "failed": failed,
        "pass_rate": d.get("pass_rate", 0),
        "avg_f1": d.get("avg_f1", 0),
        "avg_quality": d.get("avg_quality_score", 0),
        "status": "completed",
        "by_doc_type": d.get("by_doc_type", {}),
        "failures": [],
    }
    _reports[report_id] = data

    if _reports:
        prev = list(_reports.values())
        if len(prev) >= 2:
            curr = prev[-1]
            last = prev[-2]
            drift = {
                "from_report": last["id"],
                "to_report": curr["id"],
                "quality_delta": curr["avg_quality"] - last.get("avg_quality", 0),
                "f1_delta": curr["avg_f1"] - last.get("avg_f1", 0),
                "pass_rate_delta": curr["pass_rate"] - last["pass_rate"],
                "regression": curr["avg_f1"] < last.get("avg_f1", 0) - 0.01,
            }
            _drift_reports.append(drift)

    return ReportResponse(**data)


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports():
    return [ReportResponse(**r) for r in _reports.values()]


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    r = _reports.get(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(**r)


@router.get("/drift")
async def get_drift_reports():
    return _drift_reports
