"""Background job queue — async document processing.

Uses ARQ (async Redis queue) when Redis is available,
falls back to asyncio.create_task for in-process execution.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_job_results: dict[str, dict] = {}


async def enqueue_parse_job(
    file_bytes: bytes,
    filename: str,
    tier: str,
    tenant_id: str = "",
    user_id: str = "",
) -> str:
    job_id = uuid.uuid4().hex[:16]
    _job_results[job_id] = {"status": "pending", "job_id": job_id}

    from pixora.config.settings import settings
    if settings.redis_url:
        try:
            from arq import create_pool
            from arq.connections import RedisSettings
            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            await pool.enqueue_job(
                "process_document_job",
                job_id=job_id, filename=filename, tier=tier,
                tenant_id=tenant_id, user_id=user_id,
                _job_id=job_id,
            )
            logger.info("jobs: enqueued %s via ARQ", job_id)
            return job_id
        except Exception as exc:
            logger.warning("jobs: ARQ unavailable (%s), running inline", exc)

    asyncio.create_task(_run_inline(job_id, file_bytes, filename, tier, tenant_id))
    return job_id


async def _run_inline(job_id: str, file_bytes: bytes, filename: str, tier: str, tenant_id: str):
    _job_results[job_id] = {"status": "processing", "job_id": job_id}
    try:
        from pixora.api.routers.parse import _run_pipeline
        result = await _run_pipeline(file_bytes, filename, job_id, tier)
        _job_results[job_id] = {"status": "completed", "job_id": job_id, **result}
    except Exception as exc:
        _job_results[job_id] = {"status": "failed", "job_id": job_id, "error": str(exc)}
        logger.error("jobs: inline job %s failed: %s", job_id, exc)


def get_job_status(job_id: str) -> dict:
    return _job_results.get(job_id, {"status": "not_found", "job_id": job_id})


async def process_document_job(ctx: dict, **kwargs):
    """ARQ worker function — runs in background worker process."""
    job_id = kwargs.get("job_id", "")
    logger.info("jobs: ARQ worker processing %s", job_id)
