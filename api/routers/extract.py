from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pixora.api.models import ExtractRequest, JobResponse

router = APIRouter(prefix="/extract", tags=["extract"])

_jobs: dict[str, dict] = {}


@router.post("", response_model=JobResponse)
async def create_extract_job(request: ExtractRequest):
    job_id = uuid.uuid4().hex
    doc_id = uuid.uuid4().hex
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "document_id": doc_id,
        "file_id": request.file_id,
        "result": None,
    }
    return JobResponse(job_id=job_id, status="queued", document_id=doc_id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_extract_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)


@router.get("", response_model=list[JobResponse])
async def list_extract_jobs():
    return [JobResponse(**j) for j in _jobs.values()]
