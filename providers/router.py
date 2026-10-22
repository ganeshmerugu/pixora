"""Smart provider routing — picks the cheapest provider that meets the accuracy target.

Replaces the old "first available" logic in smart_extractor. Each routing decision
is logged so the audit trail shows why a specific provider was chosen.
"""
from __future__ import annotations
import logging
import os
import time
from typing import Any

from pixora.providers.base import PROVIDER_COSTS, ProviderCostProfile

logger = logging.getLogger(__name__)

_quality_history: dict[str, list[float]] = {}


def record_quality(provider_name: str, grounding_rate: float) -> None:
    _quality_history.setdefault(provider_name, []).append(grounding_rate)
    if len(_quality_history[provider_name]) > 500:
        _quality_history[provider_name] = _quality_history[provider_name][-500:]


def _effective_quality(provider_name: str) -> float:
    history = _quality_history.get(provider_name, [])
    if len(history) >= 10:
        return sum(history[-50:]) / len(history[-50:])
    return PROVIDER_COSTS.get(provider_name, {}).get("estimated_quality", 0.5)


def _get_available_providers() -> list[tuple[str, Any]]:
    available: list[tuple[str, Any]] = []

    available.append(("regex", None))

    if os.environ.get("K_SERVICE") or os.environ.get("GCLOUD_PROJECT"):
        try:
            from pixora.providers.vertex_ai import VertexAIProvider
            available.append(("vertex_ai", VertexAIProvider(
                project_id=os.environ.get("GCLOUD_PROJECT", ""),
                model=os.environ.get("PIXORA_VERTEX_MODEL", "gemini-2.0-flash-001"),
            )))
        except Exception as exc:
            logger.debug("router: vertex_ai unavailable: %s", exc)

    try:
        from pixora.config.settings import settings

        if settings.gemini_api_key:
            from pixora.providers.gemini_provider import GeminiProvider
            available.append(("gemini", GeminiProvider(api_key=settings.gemini_api_key)))

        if settings.groq_api_key:
            from pixora.providers.groq_provider import GroqProvider
            available.append(("groq", GroqProvider(api_key=settings.groq_api_key)))

        if settings.together_api_key:
            from pixora.providers.together_ai import TogetherAIProvider
            available.append(("together", TogetherAIProvider(api_key=settings.together_api_key)))

        if settings.anthropic_api_key:
            from pixora.providers.claude import ClaudeProvider
            available.append(("claude", ClaudeProvider(api_key=settings.anthropic_api_key)))
    except Exception as exc:
        logger.debug("router: provider discovery failed: %s", exc)

    return available


class RoutingDecision:
    def __init__(
        self,
        provider_name: str,
        provider: Any,
        reason: str,
        accuracy_target: float,
        estimated_quality: float,
        estimated_cost_per_1k: float,
        candidates_considered: int,
    ):
        self.provider_name = provider_name
        self.provider = provider
        self.reason = reason
        self.accuracy_target = accuracy_target
        self.estimated_quality = estimated_quality
        self.estimated_cost_per_1k = estimated_cost_per_1k
        self.candidates_considered = candidates_considered
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "reason": self.reason,
            "accuracy_target": self.accuracy_target,
            "estimated_quality": round(self.estimated_quality, 3),
            "estimated_cost_per_1k": self.estimated_cost_per_1k,
            "candidates_considered": self.candidates_considered,
        }


class ProviderRouter:
    def route(
        self,
        accuracy_target: float = 0.85,
        needs_vision: bool = False,
    ) -> RoutingDecision:
        available = _get_available_providers()

        candidates: list[tuple[str, Any, ProviderCostProfile, float]] = []
        for name, provider in available:
            profile = PROVIDER_COSTS.get(name)
            if not profile:
                continue
            if needs_vision and not profile.get("supports_vision"):
                continue
            if name == "regex" and needs_vision:
                continue

            quality = _effective_quality(name)
            candidates.append((name, provider, profile, quality))

        if not candidates:
            return RoutingDecision(
                provider_name="regex", provider=None, reason="no_providers_available",
                accuracy_target=accuracy_target, estimated_quality=0.55,
                estimated_cost_per_1k=0.0, candidates_considered=0,
            )

        meeting_target = [
            (n, p, prof, q) for n, p, prof, q in candidates if q >= accuracy_target
        ]

        if meeting_target:
            meeting_target.sort(key=lambda x: x[2].get("cost_per_1k_input", 0) + x[2].get("cost_per_1k_output", 0))
            name, provider, profile, quality = meeting_target[0]
            cost = profile.get("cost_per_1k_input", 0) + profile.get("cost_per_1k_output", 0)
            return RoutingDecision(
                provider_name=name, provider=provider,
                reason="cheapest_meeting_target",
                accuracy_target=accuracy_target, estimated_quality=quality,
                estimated_cost_per_1k=cost,
                candidates_considered=len(candidates),
            )

        candidates.sort(key=lambda x: -x[3])
        name, provider, profile, quality = candidates[0]
        cost = profile.get("cost_per_1k_input", 0) + profile.get("cost_per_1k_output", 0)
        return RoutingDecision(
            provider_name=name, provider=provider,
            reason="best_quality_below_target",
            accuracy_target=accuracy_target, estimated_quality=quality,
            estimated_cost_per_1k=cost,
            candidates_considered=len(candidates),
        )

    def route_with_fallbacks(
        self,
        accuracy_target: float = 0.85,
        needs_vision: bool = False,
    ) -> list[RoutingDecision]:
        available = _get_available_providers()

        scored: list[tuple[str, Any, float, float]] = []
        for name, provider in available:
            profile = PROVIDER_COSTS.get(name)
            if not profile:
                continue
            if needs_vision and not profile.get("supports_vision"):
                continue
            if name == "regex" and needs_vision:
                continue

            quality = _effective_quality(name)
            cost = profile.get("cost_per_1k_input", 0) + profile.get("cost_per_1k_output", 0)
            scored.append((name, provider, quality, cost))

        scored.sort(key=lambda x: (-min(x[2], accuracy_target), x[3]))

        decisions = []
        for name, provider, quality, cost in scored:
            decisions.append(RoutingDecision(
                provider_name=name, provider=provider,
                reason="fallback_chain",
                accuracy_target=accuracy_target,
                estimated_quality=quality,
                estimated_cost_per_1k=cost,
                candidates_considered=len(scored),
            ))
        return decisions
