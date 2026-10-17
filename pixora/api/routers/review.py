from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

router = APIRouter(prefix="/review", tags=["review"])

_review_queue: dict[str, dict] = {}


class ReviewItemResponse(BaseModel):
    id: str
    job_id: str
    document_id: str
    status: str = "pending"
    priority: int = 0
    quality_score: float = 0.0
    issues: list[dict[str, Any]] = Field(default_factory=list)


class ReviewSubmission(BaseModel):
    status: str
    corrections: dict[str, Any] = Field(default_factory=dict)
    reviewer: str = ""


def enqueue_review(job_id: str, document_id: str, quality_score: float, issues: list[dict]) -> str:
    review_id = uuid.uuid4().hex[:16]
    _review_queue[review_id] = {
        "id": review_id, "job_id": job_id, "document_id": document_id,
        "status": "pending", "priority": 1 if quality_score < 0.7 else 0,
        "quality_score": quality_score, "issues": issues,
    }
    return review_id


@router.get("/queue", response_model=list[ReviewItemResponse])
async def get_review_queue():
    items = sorted(_review_queue.values(), key=lambda x: (-x["priority"], x["quality_score"]))
    return [ReviewItemResponse(**i) for i in items]


@router.get("/{doc_id}", response_model=ReviewItemResponse)
async def get_review_item(doc_id: str):
    for item in _review_queue.values():
        if item["document_id"] == doc_id or item["id"] == doc_id:
            return ReviewItemResponse(**item)
    raise HTTPException(status_code=404, detail="Review item not found")


@router.post("/{doc_id}", response_model=ReviewItemResponse)
async def submit_review(doc_id: str, submission: ReviewSubmission):
    for item in _review_queue.values():
        if item["document_id"] == doc_id or item["id"] == doc_id:
            item["status"] = submission.status
            return ReviewItemResponse(**item)
    raise HTTPException(status_code=404, detail="Review item not found")
