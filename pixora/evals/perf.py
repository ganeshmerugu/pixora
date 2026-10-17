from __future__ import annotations
import math
import time
import tracemalloc
from typing import Any
from typing_extensions import Required, TypedDict


class LatencyMetrics(TypedDict, total=False):
    p50_ms: Required[float]
    p90_ms: Required[float]
    p95_ms: Required[float]
    p99_ms: Required[float]
    mean_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float


class ThroughputMetrics(TypedDict, total=False):
    docs_per_second: Required[float]
    pages_per_second: float
    fields_per_second: float


class MemoryMetrics(TypedDict, total=False):
    peak_rss_mb: Required[float]
    avg_rss_mb: float
    delta_mb: float


class PerfBenchmarkResult(TypedDict, total=False):
    suite_name: str
    total_docs: Required[int]
    total_elapsed_ms: float
    latency: Required[LatencyMetrics]
    throughput: Required[ThroughputMetrics]
    memory: MemoryMetrics
    per_doc_type: dict[str, LatencyMetrics]
    metadata: dict[str, Any]


def compute_percentiles(values: list[float]) -> LatencyMetrics:
    if not values:
        return LatencyMetrics(p50_ms=0.0, p90_ms=0.0, p95_ms=0.0, p99_ms=0.0)
    s = sorted(values)
    n = len(s)

    def _pct(k: float) -> float:
        idx = math.ceil(k / 100.0 * n) - 1
        return round(s[max(0, min(idx, n - 1))], 4)

    mean = sum(s) / n
    variance = sum((x - mean) ** 2 for x in s) / n
    return LatencyMetrics(
        p50_ms=_pct(50),
        p90_ms=_pct(90),
        p95_ms=_pct(95),
        p99_ms=_pct(99),
        mean_ms=round(mean, 4),
        min_ms=round(s[0], 4),
        max_ms=round(s[-1], 4),
        std_dev_ms=round(math.sqrt(variance), 4),
    )


def compute_throughput(
    total_docs: int,
    total_elapsed_s: float,
    total_pages: int = 0,
    total_fields: int = 0,
) -> ThroughputMetrics:
    if total_elapsed_s <= 0:
        return ThroughputMetrics(docs_per_second=0.0)
    result = ThroughputMetrics(
        docs_per_second=round(total_docs / total_elapsed_s, 4),
    )
    if total_pages > 0:
        result["pages_per_second"] = round(total_pages / total_elapsed_s, 4)
    if total_fields > 0:
        result["fields_per_second"] = round(total_fields / total_elapsed_s, 4)
    return result


async def run_perf_benchmark(
    run_fn,
    benchmarks: list[dict],
    warmup_count: int = 3,
    measure_memory: bool = True,
) -> PerfBenchmarkResult:
    warmup_items = benchmarks[:warmup_count] if len(benchmarks) >= warmup_count else benchmarks
    for item in warmup_items:
        await run_fn(item)

    doc_latencies: list[float] = []
    doc_type_latencies: dict[str, list[float]] = {}
    total_pages = 0
    total_fields = 0

    if measure_memory:
        tracemalloc.start()

    overall_start = time.monotonic()

    for bench in benchmarks:
        start = time.monotonic()
        result = await run_fn(bench)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        doc_latencies.append(elapsed_ms)

        doc_type = bench.get("doc_type", "unknown")
        doc_type_latencies.setdefault(doc_type, []).append(elapsed_ms)

        total_pages += bench.get("page_count", 1)
        if isinstance(result, dict):
            extraction = result.get("extraction_result") or result.get("extraction", {})
            if isinstance(extraction, dict):
                total_fields += len(extraction)

    total_elapsed_s = time.monotonic() - overall_start

    mem: MemoryMetrics | None = None
    if measure_memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        mem = MemoryMetrics(peak_rss_mb=round(peak / (1024 * 1024), 4))

    per_doc_type = {dt: compute_percentiles(lats) for dt, lats in doc_type_latencies.items()}

    report = PerfBenchmarkResult(
        suite_name="perf_benchmark",
        total_docs=len(benchmarks),
        total_elapsed_ms=round(total_elapsed_s * 1000.0, 4),
        latency=compute_percentiles(doc_latencies),
        throughput=compute_throughput(len(benchmarks), total_elapsed_s, total_pages, total_fields),
        per_doc_type=per_doc_type,
    )
    if mem:
        report["memory"] = mem
    return report
