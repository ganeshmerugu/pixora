from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/hitl", tags=["hitl"])

_correction_store: dict[str, list[dict]] = {}
_learned_terms: set[str] = set()


class CorrectionRequest(BaseModel):
    field: str
    original_value: str
    corrected_value: str
    corrector: str = "human"


class CorrectionResponse(BaseModel):
    job_id: str
    field: str
    accepted: bool


@router.post("/{job_id}/corrections", response_model=CorrectionResponse)
async def submit_correction(job_id: str, req: CorrectionRequest):
    correction = {
        "field": req.field,
        "original": req.original_value,
        "corrected": req.corrected_value,
        "corrector": req.corrector,
    }
    _correction_store.setdefault(job_id, []).append(correction)

    words = req.corrected_value.lower().split()
    for w in words:
        if len(w) > 3:
            _learned_terms.add(w)

    return CorrectionResponse(job_id=job_id, field=req.field, accepted=True)


@router.get("/{job_id}/corrections")
async def get_corrections(job_id: str):
    corrections = _correction_store.get(job_id, [])
    return {"job_id": job_id, "corrections": corrections, "count": len(corrections)}


@router.get("/learned-terms")
async def get_learned_terms():
    return {"terms": sorted(_learned_terms), "count": len(_learned_terms)}


def get_learned_dictionary() -> frozenset[str]:
    return frozenset(_learned_terms)
