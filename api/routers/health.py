from __future__ import annotations
from fastapi import APIRouter
from pixora.config.settings import settings

router = APIRouter(tags=["health"])

_budget_tracker = None


def get_budget_tracker():
    global _budget_tracker
    if _budget_tracker is None:
        from pixora.config.serverless_config import BudgetTracker
        _budget_tracker = BudgetTracker(limit_usd=settings.budget_limit_usd)
    return _budget_tracker


@router.get("/health")
async def health_check():
    import os
    from pixora.providers.typesafe_jev import is_available as jev_available
    providers = {
        "tesseract": True,
        "jev_typesafe": jev_available(),
        "vertex_ai": bool(os.environ.get("GCLOUD_PROJECT")),
        "gemini_vlm": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
        "together_ai": bool(settings.together_api_key),
        "replicate": bool(settings.replicate_api_token),
        "claude": bool(settings.anthropic_api_key),
    }
    api_keys_required = False

    return {
        "status": "ok",
        "service": "pixora",
        "version": "0.1.0",
        "deployment_mode": settings.deployment_mode,
        "default_tier": settings.default_tier,
        "api_keys_required": api_keys_required,
        "providers": providers,
        "note": "Pixora works fully without API keys using Tesseract OCR + heuristic extraction. API providers are optional upgrades.",
    }


@router.get("/budget")
async def budget_status():
    tracker = get_budget_tracker()
    return tracker.get_status()
