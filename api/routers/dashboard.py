"""Dashboard stats endpoint — runs real golden benchmarks through the actual
Pixora pipeline and returns real aggregated metrics. No mock data."""
from __future__ import annotations
import asyncio
from fastapi import APIRouter
from pixora.pipeline_runner import run_all_benchmarks, AggregateStats
from pixora.api.routers.parse import _jobs as parse_jobs
from pixora.api.routers.extract import _jobs as extract_jobs
from pixora.api.routers.classify import _jobs as classify_jobs

router = APIRouter(tags=["dashboard"])

_cached_stats: dict | None = None


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    global _cached_stats
    if _cached_stats is None:
        stats = await run_all_benchmarks()
        _cached_stats = stats.to_dict()

    all_jobs = list(parse_jobs.values()) + list(extract_jobs.values()) + list(classify_jobs.values())
    completed = sum(1 for j in all_jobs if j.get("status") == "completed")
    queued = sum(1 for j in all_jobs if j.get("status") == "queued")
    failed = sum(1 for j in all_jobs if j.get("status") == "failed")
    cancelled = sum(1 for j in all_jobs if j.get("status") == "cancelled")

    return {
        "jobs": {
            "total": len(all_jobs),
            "completed": completed,
            "queued": queued,
            "failed": failed,
            "cancelled": cancelled,
        },
        "benchmarks": _cached_stats,
    }


@router.post("/dashboard/refresh")
async def refresh_dashboard_stats():
    global _cached_stats
    stats = await run_all_benchmarks()
    _cached_stats = stats.to_dict()
    return _cached_stats


@router.get("/dashboard/benchmark-results")
async def get_benchmark_results():
    global _cached_stats
    if _cached_stats is None:
        stats = await run_all_benchmarks()
        _cached_stats = stats.to_dict()
    return _cached_stats.get("results", [])
