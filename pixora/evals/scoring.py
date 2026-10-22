from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.metrics import EvalMetrics


class EvalScore(TypedDict, total=False):
    document_id: str
    weighted_score: Required[float]
    passed: Required[bool]
    threshold: float
    component_scores: dict[str, float]
    metadata: dict[str, Any]


DEFAULT_EVAL_WEIGHTS: dict[str, float] = {
    "f1": 3.0,
    "exact_match_rate": 2.0,
    "precision": 1.5,
    "recall": 1.5,
    "layout_accuracy": 1.0,
    "table_f1": 2.0,
    "calibration_ece_inv": 0.5,
    "dedup_f1": 0.5,
}


def score_eval(
    metrics: EvalMetrics,
    weights: dict[str, float] | None = None,
    threshold: float = 0.80,
) -> EvalScore:
    w = weights or DEFAULT_EVAL_WEIGHTS
    components: dict[str, float] = {}
    total_weight = 0.0
    weighted_sum = 0.0

    for key, weight in w.items():
        val = metrics.get(key)  # type: ignore[arg-type]
        if val is not None and isinstance(val, (int, float)):
            components[key] = float(val)
            weighted_sum += float(val) * weight
            total_weight += weight

    score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    return EvalScore(
        document_id=metrics.get("document_id", ""),
        weighted_score=score,
        passed=score >= threshold,
        threshold=threshold,
        component_scores=components,
    )
