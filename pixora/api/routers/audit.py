"""Audit log — tracks every pipeline operation, service call, token cost, and timing.
Enterprise-grade observability like Atom AI."""
from __future__ import annotations
import time
import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["audit"])

_audit_log: list[dict] = []
_service_calls: list[dict] = []


def log_event(
    event_type: str,
    job_id: str = "",
    document_id: str = "",
    agent: str = "",
    detail: str = "",
    duration_ms: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:16],
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "job_id": job_id,
        "document_id": document_id,
        "agent": agent,
        "detail": detail,
        "duration_ms": duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 6),
        "metadata": metadata or {},
    }
    _audit_log.append(entry)
    return entry


def log_service_call(
    service: str,
    operation: str,
    job_id: str = "",
    duration_ms: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    status: str = "ok",
    error: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:16],
        "timestamp": datetime.now().isoformat(),
        "service": service,
        "operation": operation,
        "job_id": job_id,
        "duration_ms": duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 6),
        "status": status,
        "error": error,
        "metadata": metadata or {},
    }
    _service_calls.append(entry)
    return entry


class PipelineAuditor:
    """Wraps around a pipeline run and logs every stage."""
    def __init__(self, job_id: str, document_id: str):
        self.job_id = job_id
        self.document_id = document_id
        self._start = time.monotonic()
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_cost = 0.0
        self.stages: list[dict] = []

        log_event("pipeline_start", job_id=job_id, document_id=document_id, detail="Pipeline started")

    def log_stage(self, agent: str, detail: str = "", duration_ms: int = 0, tokens_in: int = 0, tokens_out: int = 0, cost_usd: float = 0.0):
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_cost += cost_usd

        stage = {
            "agent": agent, "detail": detail, "duration_ms": duration_ms,
            "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd,
        }
        self.stages.append(stage)

        log_event(
            "stage_complete", job_id=self.job_id, document_id=self.document_id,
            agent=agent, detail=detail, duration_ms=duration_ms,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
        )

        log_service_call(
            service="pixora_pipeline", operation=agent,
            job_id=self.job_id, duration_ms=duration_ms,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
        )

    def finish(self, status: str = "completed", recommendation: str = "", quality_score: float = 0.0):
        elapsed = int((time.monotonic() - self._start) * 1000)
        log_event(
            "pipeline_complete", job_id=self.job_id, document_id=self.document_id,
            detail=f"status={status}, recommendation={recommendation}, quality={quality_score:.2f}",
            duration_ms=elapsed,
            tokens_in=self.total_tokens_in, tokens_out=self.total_tokens_out,
            cost_usd=self.total_cost,
            metadata={
                "status": status, "recommendation": recommendation,
                "quality_score": quality_score, "stages": len(self.stages),
                "total_tokens": self.total_tokens_in + self.total_tokens_out,
            },
        )

    def get_summary(self) -> dict:
        elapsed = int((time.monotonic() - self._start) * 1000)
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "total_duration_ms": elapsed,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_tokens": self.total_tokens_in + self.total_tokens_out,
            "total_cost_usd": round(self.total_cost, 6),
            "stages": self.stages,
        }


@router.get("/log")
async def get_audit_log(limit: int = 100, event_type: str = ""):
    entries = _audit_log
    if event_type:
        entries = [e for e in entries if e["event_type"] == event_type]
    return {
        "total": len(entries),
        "entries": list(reversed(entries[-limit:])),
    }


@router.get("/service-calls")
async def get_service_calls(limit: int = 100, service: str = ""):
    entries = _service_calls
    if service:
        entries = [e for e in entries if e["service"] == service]
    return {
        "total": len(entries),
        "entries": list(reversed(entries[-limit:])),
    }


@router.get("/costs")
async def get_cost_summary():
    total_tokens_in = sum(e.get("tokens_in", 0) for e in _service_calls)
    total_tokens_out = sum(e.get("tokens_out", 0) for e in _service_calls)
    total_cost = sum(e.get("cost_usd", 0) for e in _service_calls)
    total_calls = len(_service_calls)

    by_operation: dict[str, dict] = {}
    for e in _service_calls:
        op = e.get("operation", "unknown")
        if op not in by_operation:
            by_operation[op] = {"calls": 0, "tokens": 0, "cost_usd": 0.0, "avg_duration_ms": 0, "total_duration_ms": 0}
        by_operation[op]["calls"] += 1
        by_operation[op]["tokens"] += e.get("tokens_in", 0) + e.get("tokens_out", 0)
        by_operation[op]["cost_usd"] += e.get("cost_usd", 0)
        by_operation[op]["total_duration_ms"] += e.get("duration_ms", 0)

    for op in by_operation:
        c = by_operation[op]["calls"]
        by_operation[op]["avg_duration_ms"] = by_operation[op]["total_duration_ms"] // max(c, 1)
        by_operation[op]["cost_usd"] = round(by_operation[op]["cost_usd"], 6)

    return {
        "total_calls": total_calls,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "total_tokens": total_tokens_in + total_tokens_out,
        "total_cost_usd": round(total_cost, 6),
        "by_operation": by_operation,
    }


@router.get("/jobs/{job_id}")
async def get_job_audit(job_id: str):
    entries = [e for e in _audit_log if e["job_id"] == job_id]
    calls = [e for e in _service_calls if e["job_id"] == job_id]

    total_tokens = sum(e.get("tokens_in", 0) + e.get("tokens_out", 0) for e in calls)
    total_cost = sum(e.get("cost_usd", 0) for e in calls)
    total_duration = sum(e.get("duration_ms", 0) for e in calls)

    return {
        "job_id": job_id,
        "events": entries,
        "service_calls": calls,
        "summary": {
            "total_events": len(entries),
            "total_service_calls": len(calls),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "total_duration_ms": total_duration,
        },
    }
