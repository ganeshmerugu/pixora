from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class CostDecision(TypedDict, total=False):
    stage: Required[str]
    action: Required[str]
    reason: str
    tokens_consumed_so_far: int
    budget_remaining: int
    quality_score_so_far: float


class CostReport(TypedDict, total=False):
    document_id: str
    total_tokens: int
    total_cost_usd: float
    cost_per_field: float
    decisions: list[CostDecision]
    quality_vs_cost_ratio: float


COST_PER_1K_TOKENS = 0.003


class CostGovernor:
    def __init__(self, budget_tokens: int = 100_000):
        self.budget_tokens = budget_tokens
        self._consumed: int = 0
        self._decisions: list[CostDecision] = []

    def check(self, stage: str, estimated_tokens: int, quality_so_far: float = 0.0) -> CostDecision:
        remaining = self.budget_tokens - self._consumed

        if estimated_tokens <= remaining:
            action = "proceed"
            reason = "within_budget"
        elif quality_so_far >= 0.75 and estimated_tokens > remaining:
            action = "skip"
            reason = "quality_sufficient_budget_exceeded"
        elif remaining > 0:
            action = "downgrade"
            reason = "budget_low_downgrade_model"
        else:
            action = "halt"
            reason = "budget_exhausted"

        decision = CostDecision(
            stage=stage,
            action=action,
            reason=reason,
            tokens_consumed_so_far=self._consumed,
            budget_remaining=remaining,
            quality_score_so_far=quality_so_far,
        )
        self._decisions.append(decision)
        return decision

    def record_usage(self, tokens: int) -> None:
        self._consumed += tokens

    def get_report(
        self,
        document_id: str = "",
        fields_extracted: int = 1,
        quality_score: float = 0.0,
    ) -> CostReport:
        cost_usd = (self._consumed / 1000) * COST_PER_1K_TOKENS
        quality_vs_cost = round(quality_score / max(cost_usd, 1e-6), 4) if cost_usd > 0 else 0.0
        return CostReport(
            document_id=document_id,
            total_tokens=self._consumed,
            total_cost_usd=round(cost_usd, 6),
            cost_per_field=round(cost_usd / max(fields_extracted, 1), 6),
            decisions=list(self._decisions),
            quality_vs_cost_ratio=quality_vs_cost,
        )

    @property
    def remaining(self) -> int:
        return max(0, self.budget_tokens - self._consumed)

    @property
    def consumed(self) -> int:
        return self._consumed
