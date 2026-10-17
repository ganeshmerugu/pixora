from __future__ import annotations
import math
from typing import Any
from typing_extensions import Required, TypedDict


class CostEfficiencyReport(TypedDict, total=False):
    avg_cost_per_doc: Required[float]
    avg_cost_per_field: Required[float]
    avg_quality_per_dollar: Required[float]
    cost_quality_correlation: float
    marginal_quality_per_round: list[float]
    optimal_rounds: int
    total_cost_usd: float
    total_documents: int
    by_doc_type: dict[str, dict[str, float]]
    metadata: dict[str, Any]


def _pearson_correlation(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


def evaluate_cost_efficiency(
    results: list[dict],
    marginal_threshold: float = 0.02,
) -> CostEfficiencyReport:
    if not results:
        return CostEfficiencyReport(
            avg_cost_per_doc=0.0, avg_cost_per_field=0.0,
            avg_quality_per_dollar=0.0, optimal_rounds=1,
        )

    costs: list[float] = []
    qualities: list[float] = []
    fields_counts: list[int] = []
    round_qualities: dict[int, list[float]] = {}
    doc_type_data: dict[str, dict[str, list[float]]] = {}

    for r in results:
        cost_report = r.get("cost_report") or {}
        cost_usd = float(cost_report.get("total_cost_usd", 0.0))
        costs.append(cost_usd)

        score = r.get("score") or {}
        quality = float(score.get("weighted_score", 0.0))
        qualities.append(quality)

        extraction = r.get("extraction_result") or r.get("extraction", {})
        n_fields = len(extraction) if isinstance(extraction, dict) else 0
        fields_counts.append(n_fields)

        correction_rounds = int(r.get("correction_rounds", 1))
        for rnd in range(1, correction_rounds + 1):
            round_qualities.setdefault(rnd, []).append(quality)

        doc_type = r.get("doc_type", "unknown")
        dt = doc_type_data.setdefault(doc_type, {"costs": [], "qualities": []})
        dt["costs"].append(cost_usd)
        dt["qualities"].append(quality)

    total_cost = sum(costs)
    total_fields = sum(fields_counts)
    n = len(results)

    avg_cost_per_doc = round(total_cost / n, 6) if n else 0.0
    avg_cost_per_field = round(total_cost / max(total_fields, 1), 6)
    avg_quality = sum(qualities) / n if n else 0.0
    avg_quality_per_dollar = round(avg_quality / max(total_cost / n, 1e-6), 4) if n else 0.0

    correlation = _pearson_correlation(costs, qualities)

    sorted_rounds = sorted(round_qualities.keys())
    marginal: list[float] = []
    prev_avg = 0.0
    optimal = 1
    for rnd in sorted_rounds:
        avg_q = sum(round_qualities[rnd]) / len(round_qualities[rnd])
        delta = round(avg_q - prev_avg, 4)
        marginal.append(delta)
        if delta >= marginal_threshold:
            optimal = rnd
        prev_avg = avg_q

    by_doc_type: dict[str, dict[str, float]] = {}
    for dt, data in doc_type_data.items():
        dt_n = len(data["costs"])
        dt_total_cost = sum(data["costs"])
        dt_avg_quality = sum(data["qualities"]) / dt_n if dt_n else 0.0
        by_doc_type[dt] = {
            "avg_cost": round(dt_total_cost / dt_n, 6) if dt_n else 0.0,
            "avg_quality": round(dt_avg_quality, 4),
            "quality_per_dollar": round(
                dt_avg_quality / max(dt_total_cost / dt_n, 1e-6), 4
            ) if dt_n else 0.0,
            "count": float(dt_n),
        }

    return CostEfficiencyReport(
        avg_cost_per_doc=avg_cost_per_doc,
        avg_cost_per_field=avg_cost_per_field,
        avg_quality_per_dollar=avg_quality_per_dollar,
        cost_quality_correlation=correlation,
        marginal_quality_per_round=marginal,
        optimal_rounds=optimal,
        total_cost_usd=round(total_cost, 6),
        total_documents=n,
        by_doc_type=by_doc_type,
    )
