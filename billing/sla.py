"""Accuracy SLA pricing — customers pay by guaranteed accuracy tier.

Each SLA tier defines a minimum grounding rate, the provider strategy to achieve it,
and the price multiplier over the base per-document rate.
"""
from __future__ import annotations
from typing_extensions import Required, TypedDict


class SLATier(TypedDict, total=False):
    name: Required[str]
    display_name: Required[str]
    accuracy_target: Required[float]
    max_correction_rounds: Required[int]
    price_multiplier: Required[float]
    human_review_fallback: Required[bool]
    description: str


SLA_TIERS: dict[str, SLATier] = {
    "standard": SLATier(
        name="standard",
        display_name="Standard",
        accuracy_target=0.85,
        max_correction_rounds=1,
        price_multiplier=1.0,
        human_review_fallback=False,
        description="Best-effort extraction using the cheapest available provider. Suitable for bulk processing where some errors are acceptable.",
    ),
    "premium": SLATier(
        name="premium",
        display_name="Premium",
        accuracy_target=0.95,
        max_correction_rounds=3,
        price_multiplier=3.0,
        human_review_fallback=False,
        description="High-accuracy extraction with self-correction. Uses the best available provider and retries with corrections.",
    ),
    "guaranteed": SLATier(
        name="guaranteed",
        display_name="Guaranteed",
        accuracy_target=0.99,
        max_correction_rounds=5,
        price_multiplier=10.0,
        human_review_fallback=True,
        description="Near-perfect accuracy with human review fallback. If AI can't reach 99%, a human reviewer verifies the extraction.",
    ),
}

DEFAULT_SLA_TIER = "standard"

BASE_PRICE_PER_DOC_USD = 0.01


class SLAEnforcementResult(TypedDict, total=False):
    tier: Required[str]
    accuracy_target: Required[float]
    achieved_accuracy: Required[float]
    met_sla: Required[bool]
    action: Required[str]
    reason: str
    price_usd: float


def get_sla_tier(name: str) -> SLATier:
    return SLA_TIERS.get(name, SLA_TIERS[DEFAULT_SLA_TIER])


def compute_price(tier_name: str, base_price: float = BASE_PRICE_PER_DOC_USD) -> float:
    tier = get_sla_tier(tier_name)
    return round(base_price * tier["price_multiplier"], 4)


def enforce_sla(
    tier_name: str,
    grounding_rate: float,
    correction_round: int,
) -> SLAEnforcementResult:
    tier = get_sla_tier(tier_name)
    target = tier["accuracy_target"]
    max_rounds = tier["max_correction_rounds"]
    met = grounding_rate >= target

    if met:
        return SLAEnforcementResult(
            tier=tier_name, accuracy_target=target,
            achieved_accuracy=grounding_rate, met_sla=True,
            action="accept", reason="accuracy_target_met",
            price_usd=compute_price(tier_name),
        )

    if correction_round < max_rounds - 1:
        return SLAEnforcementResult(
            tier=tier_name, accuracy_target=target,
            achieved_accuracy=grounding_rate, met_sla=False,
            action="retry_upgraded", reason="below_target_retrying_with_better_provider",
            price_usd=compute_price(tier_name),
        )

    if tier.get("human_review_fallback") and grounding_rate < target:
        return SLAEnforcementResult(
            tier=tier_name, accuracy_target=target,
            achieved_accuracy=grounding_rate, met_sla=False,
            action="escalate_human", reason="exhausted_ai_corrections_escalating_to_human_review",
            price_usd=compute_price(tier_name),
        )

    return SLAEnforcementResult(
        tier=tier_name, accuracy_target=target,
        achieved_accuracy=grounding_rate, met_sla=False,
        action="accept_with_warning", reason="best_effort_exhausted",
        price_usd=compute_price(tier_name),
    )


def get_tier_for_plan(plan_name: str) -> str:
    plan_sla_map = {
        "free_trial": "standard",
        "starter": "standard",
        "pro": "premium",
        "enterprise": "guaranteed",
    }
    return plan_sla_map.get(plan_name, DEFAULT_SLA_TIER)
