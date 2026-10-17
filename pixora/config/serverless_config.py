from __future__ import annotations
import logging
from typing import Any
from typing_extensions import Required, TypedDict

logger = logging.getLogger(__name__)


class BudgetStatus(TypedDict, total=False):
    total_spent_usd: Required[float]
    budget_limit_usd: Required[float]
    remaining_usd: float
    total_requests: int
    budget_exceeded: bool
    by_provider: dict[str, float]


class BudgetTracker:
    def __init__(self, limit_usd: float = 1.0):
        self.limit_usd = limit_usd
        self._spent: float = 0.0
        self._requests: int = 0
        self._by_provider: dict[str, float] = {}

    def can_spend(self, estimated_cost: float = 0.01) -> bool:
        return (self._spent + estimated_cost) <= self.limit_usd

    def record(self, provider: str, cost_usd: float) -> None:
        self._spent += cost_usd
        self._requests += 1
        self._by_provider[provider] = self._by_provider.get(provider, 0.0) + cost_usd

        if self._spent >= self.limit_usd * 0.8:
            remaining = self.limit_usd - self._spent
            logger.warning("budget: 80%% threshold reached. Remaining: $%.4f", remaining)

    def get_status(self) -> BudgetStatus:
        remaining = max(0.0, self.limit_usd - self._spent)
        return BudgetStatus(
            total_spent_usd=round(self._spent, 6),
            budget_limit_usd=self.limit_usd,
            remaining_usd=round(remaining, 6),
            total_requests=self._requests,
            budget_exceeded=self._spent >= self.limit_usd,
            by_provider={k: round(v, 6) for k, v in self._by_provider.items()},
        )

    def reset(self) -> None:
        self._spent = 0.0
        self._requests = 0
        self._by_provider.clear()


SERVERLESS_PROVIDER_PRIORITY = [
    {"provider": "groq", "capability": "llm", "reason": "cheapest, fastest"},
    {"provider": "together_ai", "capability": "llm", "reason": "more models, good fallback"},
    {"provider": "replicate", "capability": "vlm", "reason": "serverless GPU, pay per image"},
    {"provider": "claude", "capability": "llm", "reason": "best quality, expensive fallback"},
]


def get_recommended_provider(capability: str, budget_remaining: float) -> str:
    if capability in ("extraction", "classification", "llm"):
        if budget_remaining > 0.10:
            return "groq"
        if budget_remaining > 0.01:
            return "groq"
        return "basic"
    if capability in ("vision", "vlm"):
        if budget_remaining > 0.10:
            return "replicate"
        return "basic"
    return "basic"
