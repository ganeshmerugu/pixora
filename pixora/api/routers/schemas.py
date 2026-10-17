from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from pixora.models.ontology import validate_schema
from pixora.extraction.llm_engine import generate_schema_with_llm, is_available as llm_available
from pixora.storage import get_file

router = APIRouter(prefix="/schemas", tags=["schemas"])

_schemas: dict[str, dict] = {}


class SchemaCreateRequest(BaseModel):
    name: str
    doc_type: str
    version: str = "1.0"
    nodes: list[dict[str, Any]]


class SchemaResponse(BaseModel):
    id: str
    name: str
    doc_type: str
    version: str
    nodes: list[dict[str, Any]]


@router.post("", response_model=SchemaResponse)
async def create_schema(request: SchemaCreateRequest):
    schema_id = uuid.uuid4().hex[:16]
    data = {"id": schema_id, **request.model_dump()}
    _schemas[schema_id] = data
    return SchemaResponse(**data)


@router.get("", response_model=list[SchemaResponse])
async def list_schemas():
    return [SchemaResponse(**s) for s in _schemas.values()]


@router.get("/{schema_id}", response_model=SchemaResponse)
async def get_schema(schema_id: str):
    s = _schemas.get(schema_id)
    if not s:
        raise HTTPException(status_code=404, detail="Schema not found")
    return SchemaResponse(**s)


@router.put("/{schema_id}", response_model=SchemaResponse)
async def update_schema(schema_id: str, request: SchemaCreateRequest):
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail="Schema not found")
    data = {"id": schema_id, **request.model_dump()}
    _schemas[schema_id] = data
    return SchemaResponse(**data)


@router.delete("/{schema_id}")
async def delete_schema(schema_id: str):
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail="Schema not found")
    del _schemas[schema_id]
    return {"deleted": True}


@router.post("/infer", response_model=SchemaResponse)
async def infer_schema(text: str = ""):
    schema_id = uuid.uuid4().hex[:16]
    data = {
        "id": schema_id, "name": "auto_inferred", "doc_type": "unknown",
        "version": "1.0", "nodes": [],
    }
    _schemas[schema_id] = data
    return SchemaResponse(**data)


class SchemaValidateRequest(BaseModel):
    schema_def: dict[str, Any] = Field(alias="schema")


@router.post("/validate")
async def validate_schema_endpoint(request: SchemaValidateRequest):
    errors = validate_schema(request.schema_def)
    return {"valid": len(errors) == 0, "errors": errors}


class SchemaGenerateRequest(BaseModel):
    prompt: str
    file_id: str | None = None


@router.post("/generate", response_model=SchemaResponse)
async def generate_schema(request: SchemaGenerateRequest):
    if not llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. Set PIXORA_GROQ_API_KEY or PIXORA_ANTHROPIC_API_KEY to enable schema generation. Basic extraction works without API keys.",
        )

    sample_text = None
    if request.file_id:
        stored = get_file(request.file_id)
        if stored and stored.get("data"):
            sample_text = stored["data"].decode("utf-8", errors="replace")[:10000]

    result = generate_schema_with_llm(request.prompt, sample_text)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    schema_id = uuid.uuid4().hex[:16]
    data = {
        "id": schema_id,
        "name": result.get("schema_id", "generated"),
        "doc_type": result.get("doc_type", "unknown"),
        "version": result.get("version", "1.0"),
        "nodes": result.get("nodes", []),
    }
    _schemas[schema_id] = data
    return SchemaResponse(**data)
