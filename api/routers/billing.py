from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pixora.auth.dependencies import get_current_user, get_current_tenant
from pixora.auth.models import (
    User, Tenant, check_quota, upgrade_plan, PLAN_LIMITS,
    CURRENCY_RATES, get_localized_price,
)
from pixora.billing.sla import SLA_TIERS, compute_price

router = APIRouter(prefix="/billing", tags=["billing"])


class UpgradeRequest(BaseModel):
    plan: str


@router.get("/plans")
async def list_plans(currency: str = "USD"):
    currency = currency.upper()
    if currency not in CURRENCY_RATES:
        currency = "USD"

    plans = []
    for name, info in PLAN_LIMITS.items():
        price = get_localized_price(info["price_usd"], currency)
        plans.append({
            "name": name,
            "docs_limit": info["docs_limit"],
            "monthly": info["monthly"],
            "price_usd": info["price_usd"],
            "price": price,
        })

    return {
        "plans": plans,
        "currency": currency,
        "supported_currencies": list(CURRENCY_RATES.keys()),
    }


@router.get("/plan")
async def get_current_plan(
    currency: str = "USD",
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    currency = currency.upper()
    if currency not in CURRENCY_RATES:
        currency = "USD"

    quota = check_quota(tenant["id"])
    plan_info = PLAN_LIMITS.get(tenant["plan"], PLAN_LIMITS["free_trial"])
    price = get_localized_price(plan_info["price_usd"], currency)

    return {
        "plan": tenant["plan"],
        "price_usd": plan_info["price_usd"],
        "price": price,
        "docs_used": quota["docs_used"],
        "docs_limit": quota["docs_limit"],
        "remaining": quota["remaining"],
        "usage_percent": round(quota["docs_used"] / max(quota["docs_limit"], 1) * 100, 1),
        "tenant_name": tenant["name"],
    }


@router.post("/upgrade")
async def upgrade(
    req: UpgradeRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    if req.plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}. Available: {list(PLAN_LIMITS.keys())}")

    if req.plan == tenant["plan"]:
        raise HTTPException(status_code=400, detail="Already on this plan")

    updated = upgrade_plan(tenant["id"], req.plan)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to upgrade plan")

    quota = check_quota(updated["id"])
    return {
        "message": f"Upgraded to {req.plan}",
        "plan": req.plan,
        "docs_limit": quota["docs_limit"],
        "docs_used": quota["docs_used"],
        "remaining": quota["remaining"],
    }


@router.get("/usage")
async def get_usage(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    quota = check_quota(tenant["id"])
    return {
        "plan": tenant["plan"],
        "docs_used": quota["docs_used"],
        "docs_limit": quota["docs_limit"],
        "remaining": quota["remaining"],
        "usage_percent": round(quota["docs_used"] / max(quota["docs_limit"], 1) * 100, 1),
    }


@router.get("/sla-tiers")
async def list_sla_tiers():
    tiers = []
    for name, tier in SLA_TIERS.items():
        tiers.append({
            "name": tier["name"],
            "display_name": tier["display_name"],
            "accuracy_target": tier["accuracy_target"],
            "accuracy_target_pct": f"{tier['accuracy_target'] * 100:.0f}%",
            "max_correction_rounds": tier["max_correction_rounds"],
            "price_multiplier": tier["price_multiplier"],
            "price_per_doc_usd": compute_price(name),
            "human_review_fallback": tier["human_review_fallback"],
            "description": tier.get("description", ""),
        })
    return {"sla_tiers": tiers}


@router.get("/currencies")
async def list_currencies():
    return {
        "currencies": [
            {"code": code, "symbol": info["symbol"], "rate": info["rate"]}
            for code, info in CURRENCY_RATES.items()
        ],
    }
