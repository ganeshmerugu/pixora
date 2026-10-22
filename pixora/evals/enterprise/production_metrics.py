"""Production metrics — cost per page, latency, throughput, semantic formatting.

The engineering blindspots: accuracy doesn't matter if you're too slow or expensive.
"""
from __future__ import annotations
import math
import time
from typing import Any
from typing_extensions import Required, TypedDict


class PageCostBreakdown(TypedDict, total=False):
    ocr_cost: float
    llm_cost: float
    vlm_cost: float
    total_cost: float
    tokens_used: int
    api_calls: int


class ProductionReport(TypedDict, total=False):
    # Cost metrics
    avg_cost_per_page_usd: Required[float]
    median_cost_per_page_usd: float
    p95_cost_per_page_usd: float
    total_cost_usd: float
    cost_by_tier: dict[str, float]

    # Latency metrics
    avg_latency_per_page_ms: Required[float]
    median_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    # Throughput
    pages_per_second: float
    pages_per_minute: float

    # Semantic formatting
    semantic_formatting_score: float
    strikethrough_detection_rate: float
    bold_detection_rate: float
    superscript_detection_rate: float

    total_pages: int
    per_page: list[dict[str, float]]
    metadata: dict[str, Any]


class ProductionTracker:
    def __init__(self):
        self._page_costs: list[float] = []
        self._page_latencies: list[float] = []
        self._page_details: list[dict] = []
        self._start_time: float = 0.0
        self._tier_costs: dict[str, float] = {}
        self._formatting_checks: dict[str, dict[str, int]] = {}

    def start_batch(self) -> None:
        self._start_time = time.monotonic()

    def record_page(
        self,
        cost_usd: float,
        latency_ms: float,
        tier: str = "tier1",
        tokens: int = 0,
        api_calls: int = 0,
    ) -> None:
        self._page_costs.append(cost_usd)
        self._page_latencies.append(latency_ms)
        self._tier_costs[tier] = self._tier_costs.get(tier, 0) + cost_usd
        self._page_details.append({
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "tier": tier,
            "tokens": tokens,
            "api_calls": api_calls,
        })

    def record_formatting_check(
        self,
        format_type: str,
        expected: bool,
        detected: bool,
    ) -> None:
        if format_type not in self._formatting_checks:
            self._formatting_checks[format_type] = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
        counts = self._formatting_checks[format_type]
        if expected and detected:
            counts["tp"] += 1
        elif expected and not detected:
            counts["fn"] += 1
        elif not expected and detected:
            counts["fp"] += 1
        else:
            counts["tn"] += 1

    def get_report(self) -> ProductionReport:
        n = len(self._page_costs)
        if n == 0:
            return ProductionReport(avg_cost_per_page_usd=0.0, avg_latency_per_page_ms=0.0, total_pages=0)

        costs_sorted = sorted(self._page_costs)
        lats_sorted = sorted(self._page_latencies)

        def _pct(vals: list[float], p: float) -> float:
            idx = min(int(math.ceil(p / 100 * len(vals))) - 1, len(vals) - 1)
            return round(vals[max(0, idx)], 4)

        elapsed = time.monotonic() - self._start_time if self._start_time else sum(self._page_latencies) / 1000
        pps = n / elapsed if elapsed > 0 else 0

        formatting_scores: dict[str, float] = {}
        for fmt, counts in self._formatting_checks.items():
            tp = counts["tp"]
            fn = counts["fn"]
            rate = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            formatting_scores[fmt] = round(rate, 4)

        avg_fmt = sum(formatting_scores.values()) / len(formatting_scores) if formatting_scores else 0.0

        report = ProductionReport(
            avg_cost_per_page_usd=round(sum(costs_sorted) / n, 6),
            median_cost_per_page_usd=_pct(costs_sorted, 50),
            p95_cost_per_page_usd=_pct(costs_sorted, 95),
            total_cost_usd=round(sum(costs_sorted), 6),
            cost_by_tier=dict(self._tier_costs),
            avg_latency_per_page_ms=round(sum(lats_sorted) / n, 2),
            median_latency_ms=_pct(lats_sorted, 50),
            p50_latency_ms=_pct(lats_sorted, 50),
            p90_latency_ms=_pct(lats_sorted, 90),
            p95_latency_ms=_pct(lats_sorted, 95),
            p99_latency_ms=_pct(lats_sorted, 99),
            pages_per_second=round(pps, 2),
            pages_per_minute=round(pps * 60, 1),
            semantic_formatting_score=round(avg_fmt, 4),
            strikethrough_detection_rate=formatting_scores.get("strikethrough", 0.0),
            bold_detection_rate=formatting_scores.get("bold", 0.0),
            superscript_detection_rate=formatting_scores.get("superscript", 0.0),
            total_pages=n,
            per_page=self._page_details,
        )

        return report

    def reset(self) -> None:
        self._page_costs.clear()
        self._page_latencies.clear()
        self._page_details.clear()
        self._tier_costs.clear()
        self._formatting_checks.clear()
        self._start_time = 0.0


def format_production_report(report: ProductionReport) -> str:
    lines = [
        "Production Metrics Report",
        "=" * 55,
        "",
        f"Total Pages: {report.get('total_pages', 0)}",
        "",
        "COST:",
        f"  Avg cost/page:    ${report['avg_cost_per_page_usd']:.4f}",
        f"  Median cost/page: ${report.get('median_cost_per_page_usd', 0):.4f}",
        f"  P95 cost/page:    ${report.get('p95_cost_per_page_usd', 0):.4f}",
        f"  Total cost:       ${report.get('total_cost_usd', 0):.4f}",
    ]

    tier_costs = report.get("cost_by_tier", {})
    if tier_costs:
        for tier, cost in sorted(tier_costs.items()):
            lines.append(f"    {tier}: ${cost:.4f}")

    lines.extend([
        "",
        "LATENCY:",
        f"  Avg/page:   {report['avg_latency_per_page_ms']:.0f}ms",
        f"  P50:        {report.get('p50_latency_ms', 0):.0f}ms",
        f"  P90:        {report.get('p90_latency_ms', 0):.0f}ms",
        f"  P95:        {report.get('p95_latency_ms', 0):.0f}ms",
        f"  P99:        {report.get('p99_latency_ms', 0):.0f}ms",
        "",
        "THROUGHPUT:",
        f"  Pages/second: {report.get('pages_per_second', 0):.2f}",
        f"  Pages/minute: {report.get('pages_per_minute', 0):.1f}",
    ])

    fmt_score = report.get("semantic_formatting_score", 0)
    if fmt_score > 0:
        lines.extend([
            "",
            f"SEMANTIC FORMATTING: {fmt_score * 100:.1f}%",
            f"  Bold detection:          {report.get('bold_detection_rate', 0) * 100:.1f}%",
            f"  Strikethrough detection:  {report.get('strikethrough_detection_rate', 0) * 100:.1f}%",
            f"  Superscript detection:    {report.get('superscript_detection_rate', 0) * 100:.1f}%",
        ])

    return "\n".join(lines)
