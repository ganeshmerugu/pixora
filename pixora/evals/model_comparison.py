from __future__ import annotations
import time
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.config.model_catalog import ModelSpec, MODEL_CATALOG, TIER_NAMES


class ModelBenchmarkResult(TypedDict, total=False):
    model_id: Required[str]
    model_name: str
    tier: int
    avg_f1: Required[float]
    avg_exact_match: float
    avg_score: float
    pass_rate: float
    avg_latency_ms: float
    total_cost_usd: float
    cost_per_doc: float
    docs_processed: int
    by_doc_type: dict[str, dict[str, float]]
    by_difficulty: dict[str, dict[str, float]]
    metadata: dict[str, Any]


class ComparisonReport(TypedDict, total=False):
    total_models: Required[int]
    total_benchmarks: int
    results: Required[list[ModelBenchmarkResult]]
    recommendations: dict[str, str]
    cost_comparison: dict[str, float]
    quality_ranking: list[str]
    value_ranking: list[str]
    generated_at: str
    metadata: dict[str, Any]


def build_comparison_report(results: list[ModelBenchmarkResult]) -> ComparisonReport:
    quality_sorted = sorted(results, key=lambda r: -r["avg_f1"])
    quality_ranking = [r["model_id"] for r in quality_sorted]

    def _value_score(r: ModelBenchmarkResult) -> float:
        cost = r.get("cost_per_doc", 0.001)
        return r["avg_f1"] / max(cost, 0.0001)

    value_sorted = sorted(results, key=lambda r: -_value_score(r))
    value_ranking = [r["model_id"] for r in value_sorted]

    cost_comparison = {r["model_id"]: r.get("cost_per_doc", 0.0) for r in results}

    recommendations: dict[str, str] = {}
    by_doc_types: dict[str, list[tuple[str, float]]] = {}
    for r in results:
        for dt, metrics in r.get("by_doc_type", {}).items():
            f1 = metrics.get("avg_f1", 0.0)
            by_doc_types.setdefault(dt, []).append((r["model_id"], f1))

    for dt, model_scores in by_doc_types.items():
        passing = [(mid, f1) for mid, f1 in model_scores if f1 >= 0.80]
        if passing:
            cheapest = min(passing, key=lambda x: cost_comparison.get(x[0], 999))
            recommendations[dt] = cheapest[0]
        elif model_scores:
            best = max(model_scores, key=lambda x: x[1])
            recommendations[dt] = best[0]

    return ComparisonReport(
        total_models=len(results),
        total_benchmarks=sum(r.get("docs_processed", 0) for r in results),
        results=results,
        recommendations=recommendations,
        cost_comparison=cost_comparison,
        quality_ranking=quality_ranking,
        value_ranking=value_ranking,
    )


def format_comparison_table(report: ComparisonReport) -> str:
    lines = [
        "| Model | Tier | F1 | Exact Match | Pass Rate | Latency | Cost/Doc |",
        "|-------|------|----|----|---------|---------|---------|",
    ]
    for r in sorted(report["results"], key=lambda x: -x["avg_f1"]):
        tier = TIER_NAMES.get(r.get("tier", 0), "?")
        lines.append(
            f"| {r.get('model_name', r['model_id']):25s} | {tier:10s} "
            f"| {r['avg_f1']:.4f} | {r.get('avg_exact_match', 0):.4f} "
            f"| {r.get('pass_rate', 0):.2%} | {r.get('avg_latency_ms', 0):.0f}ms "
            f"| ${r.get('cost_per_doc', 0):.4f} |"
        )

    lines.append("\n## Recommendations (cheapest model meeting 0.80 F1):")
    for dt, model_id in report.get("recommendations", {}).items():
        lines.append(f"  {dt}: {model_id}")

    lines.append("\n## Value Ranking (F1 per dollar):")
    for i, mid in enumerate(report.get("value_ranking", [])[:5]):
        lines.append(f"  {i+1}. {mid}")

    return "\n".join(lines)
