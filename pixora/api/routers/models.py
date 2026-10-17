from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from pixora.config.model_catalog import MODEL_CATALOG, TIER_NAMES, get_model, get_models_by_tier, get_models_by_capability

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    model_id: str
    name: str
    tier: int
    tier_name: str
    capabilities: list[str]
    cost_per_image: float
    cost_per_1k_tokens: float
    min_gpu_gb: float
    description: str


@router.get("")
async def list_models(tier: int | None = None, capability: str | None = None):
    models = MODEL_CATALOG
    if tier is not None:
        models = get_models_by_tier(tier)
    if capability:
        models = [m for m in models if capability in m["capabilities"]]

    return {
        "models": [
            ModelInfo(
                model_id=m["model_id"],
                name=m["name"],
                tier=m["tier"],
                tier_name=TIER_NAMES.get(m["tier"], "unknown"),
                capabilities=m["capabilities"],
                cost_per_image=m.get("cost_per_image", 0.0),
                cost_per_1k_tokens=m.get("cost_per_1k_tokens", 0.0),
                min_gpu_gb=m.get("min_gpu_gb", 0.0),
                description=m.get("description", ""),
            ).model_dump()
            for m in models
        ],
        "total": len(models),
        "tiers": TIER_NAMES,
    }


@router.get("/{model_id}")
async def get_model_detail(model_id: str):
    model = get_model(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found"}
    return dict(model)


@router.get("/tiers/{tier}")
async def get_tier_models(tier: int):
    models = get_models_by_tier(tier)
    return {
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, "unknown"),
        "models": [dict(m) for m in models],
        "total": len(models),
    }


@router.get("/capabilities/{capability}")
async def get_capability_models(capability: str):
    models = get_models_by_capability(capability)
    return {
        "capability": capability,
        "models": [
            {"model_id": m["model_id"], "name": m["name"], "tier": m["tier"]}
            for m in models
        ],
        "total": len(models),
    }
