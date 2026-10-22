from __future__ import annotations
import logging
import time
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.config.model_catalog import ModelSpec, MODEL_CATALOG, get_models_by_capability, TIER_NAMES

logger = logging.getLogger(__name__)


class InferenceResult(TypedDict, total=False):
    content: Required[str]
    model_id: Required[str]
    tier: Required[int]
    cost_usd: float
    latency_ms: float
    tokens_used: int
    escalated: bool
    escalation_reason: str
    metadata: dict[str, Any]


class ModelHubConfig(TypedDict, total=False):
    default_tier: int
    max_tier: int
    quality_threshold: float
    max_cost_per_doc: float
    enable_escalation: bool
    preferred_models: dict[str, str]


DEFAULT_HUB_CONFIG = ModelHubConfig(
    default_tier=1,
    max_tier=2,
    quality_threshold=0.80,
    max_cost_per_doc=0.01,
    enable_escalation=True,
)


class ModelHub:
    def __init__(self, config: ModelHubConfig | None = None):
        self.config = config or DEFAULT_HUB_CONFIG
        self._providers: dict[str, Any] = {}
        self._model_specs: dict[str, ModelSpec] = {m["model_id"]: m for m in MODEL_CATALOG}
        self._request_costs: list[float] = []
        self._tier_usage: dict[int, int] = {1: 0, 2: 0, 3: 0}

    def register_provider(self, model_id: str, provider: Any) -> None:
        if model_id not in self._model_specs:
            logger.warning("model_hub: unknown model_id '%s', registering anyway", model_id)
        self._providers[model_id] = provider
        logger.info("model_hub: registered provider for '%s'", model_id)

    def get_provider(self, model_id: str) -> Any:
        provider = self._providers.get(model_id)
        if not provider:
            raise KeyError(f"No provider registered for model '{model_id}'")
        return provider

    def list_available(self) -> list[dict[str, Any]]:
        result = []
        for model_id, spec in self._model_specs.items():
            result.append({
                "model_id": model_id,
                "name": spec["name"],
                "tier": spec["tier"],
                "tier_name": TIER_NAMES.get(spec["tier"], "unknown"),
                "capabilities": spec["capabilities"],
                "registered": model_id in self._providers,
                "cost_per_image": spec.get("cost_per_image", 0),
                "min_gpu_gb": spec.get("min_gpu_gb", 0),
            })
        return result

    def select_model(
        self,
        capability: str,
        preferred_tier: int | None = None,
        max_cost: float | None = None,
    ) -> ModelSpec | None:
        tier = preferred_tier or self.config.get("default_tier", 1)
        candidates = get_models_by_capability(capability)
        candidates = [c for c in candidates if c["model_id"] in self._providers]

        if max_cost is not None:
            candidates = [
                c for c in candidates
                if (c.get("cost_per_image", 0) + c.get("cost_per_1k_tokens", 0)) <= max_cost
            ]

        tier_candidates = [c for c in candidates if c["tier"] == tier]
        if tier_candidates:
            return tier_candidates[0]

        candidates.sort(key=lambda m: m["tier"])
        return candidates[0] if candidates else None

    async def infer(
        self,
        capability: str,
        request: dict[str, Any],
        quality_score: float | None = None,
    ) -> InferenceResult:
        config = self.config
        current_tier = config.get("default_tier", 1)
        max_tier = config.get("max_tier", 3)
        threshold = config.get("quality_threshold", 0.80)
        enable_escalation = config.get("enable_escalation", True)

        escalated = False
        escalation_reason = ""

        if quality_score is not None and quality_score < threshold and enable_escalation:
            current_tier = min(current_tier + 1, max_tier)
            escalated = True
            escalation_reason = f"quality {quality_score:.2f} < threshold {threshold:.2f}"
            logger.info("model_hub: escalating to tier %d — %s", current_tier, escalation_reason)

        for tier in range(current_tier, max_tier + 1):
            model = self.select_model(capability, preferred_tier=tier)
            if not model:
                continue

            model_id = model["model_id"]
            provider = self._providers.get(model_id)
            if not provider:
                continue

            start = time.monotonic()
            try:
                if capability == "ocr" and hasattr(provider, "recognize"):
                    result = await provider.recognize(
                        request.get("image_bytes", b""),
                        request.get("languages"),
                        request.get("page_number", 1),
                    )
                    content = result[0]["text"] if result else ""
                elif capability == "vision" and hasattr(provider, "analyze_image"):
                    resp = await provider.analyze_image(
                        request.get("image_bytes", b""),
                        request.get("prompt", ""),
                    )
                    content = resp.get("content", "")
                elif capability in ("extraction", "classification") and hasattr(provider, "generate"):
                    resp = await provider.generate(
                        messages=request.get("messages", []),
                        system=request.get("system", ""),
                        temperature=request.get("temperature", 0.0),
                    )
                    content = resp.get("content", "")
                else:
                    continue

                latency = (time.monotonic() - start) * 1000
                cost = model.get("cost_per_image", 0) or model.get("cost_per_1k_tokens", 0) * 0.5

                self._request_costs.append(cost)
                self._tier_usage[tier] = self._tier_usage.get(tier, 0) + 1

                return InferenceResult(
                    content=content,
                    model_id=model_id,
                    tier=tier,
                    cost_usd=round(cost, 6),
                    latency_ms=round(latency, 2),
                    escalated=escalated,
                    escalation_reason=escalation_reason,
                )

            except Exception as exc:
                logger.warning("model_hub: model '%s' failed: %s, trying next tier", model_id, exc)
                escalated = True
                escalation_reason = f"model {model_id} failed: {exc}"
                continue

        return InferenceResult(
            content="",
            model_id="none",
            tier=0,
            cost_usd=0.0,
            escalated=True,
            escalation_reason="all tiers exhausted",
        )

    def get_cost_summary(self) -> dict[str, Any]:
        total = sum(self._request_costs)
        return {
            "total_cost_usd": round(total, 6),
            "total_requests": len(self._request_costs),
            "avg_cost_per_request": round(total / max(len(self._request_costs), 1), 6),
            "tier_usage": dict(self._tier_usage),
        }

    def reset_stats(self) -> None:
        self._request_costs.clear()
        self._tier_usage = {1: 0, 2: 0, 3: 0}
