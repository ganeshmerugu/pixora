from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class TaskHypothesis(TypedDict, total=False):
    round_num: Required[int]
    current_hypothesis: str
    confidence: float
    action_taken: str
    score: float
    metadata: dict[str, Any]


class FailureAttribution(TypedDict, total=False):
    round: Required[int]
    component: str
    dimension: str
    field: str
    message: str
    severity: str
    metadata: dict[str, Any]


class VerificationReport(TypedDict, total=False):
    document_id: Required[str]
    total_rounds: int
    final_score: float
    final_recommendation: str
    hypotheses: list[TaskHypothesis]
    attributions: list[FailureAttribution]
    grounding_report: dict
    cost_report: dict
    metadata: dict[str, Any]


def build_verification_report(
    document_id: str,
    total_rounds: int,
    final_score: float,
    recommendation: str,
    hypotheses: list[dict],
    attributions: list[dict],
    grounding: dict | None = None,
    cost: dict | None = None,
) -> VerificationReport:
    return VerificationReport(
        document_id=document_id,
        total_rounds=total_rounds,
        final_score=final_score,
        final_recommendation=recommendation,
        hypotheses=hypotheses,
        attributions=attributions,
        grounding_report=grounding or {},
        cost_report=cost or {},
    )
