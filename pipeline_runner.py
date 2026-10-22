"""Runs golden benchmarks through the real Pixora agent pipeline and produces
real quality metrics, grounding reports, and scores -- no mocks."""
from __future__ import annotations
import asyncio
import importlib
import uuid
import time
from typing import Any

from pixora.agents.state import AgentState
from pixora.agents.classifier import ClassifierAgent
from pixora.agents.router import RouterAgent
from pixora.agents.extractor import ExtractorAgent
from pixora.agents.validator import ValidatorAgent
from pixora.agents.scorer import ScorerAgent
from pixora.harness.grounding import GroundingVerifier
from pixora.models.document import DocumentTree, Page, Region
from pixora.evals.noise import NoiseConfig, inject_ocr_noise

_metrics_mod = importlib.import_module("pixora.evals.metrics")
_scoring_mod = importlib.import_module("pixora.evals.scoring")
compute_metrics = _metrics_mod.compute_eval_metrics
score_fn = _scoring_mod.score_eval


class PipelineResult:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "doc_type": self.doc_type,
            "extraction": self.extraction,
            "quality_report": self.quality_report,
            "grounding_report": self.grounding_report,
            "metrics": dict(self.metrics),
            "score": dict(self.score),
            "processing_time_ms": self.processing_time_ms,
            "correction_rounds": self.correction_rounds,
        }


class AggregateStats:
    def __init__(self, results: list[PipelineResult]):
        self.results = results
        self.total = len(results)

    def _avg(self, fn) -> float:
        vals = [fn(r) for r in self.results]
        return round(sum(vals) / max(len(vals), 1), 4)

    @property
    def avg_quality_score(self): return self._avg(lambda r: r.quality_report.get("overall_score", 0))
    @property
    def avg_grounding_rate(self): return self._avg(lambda r: r.grounding_report.get("grounding_rate", 0))
    @property
    def avg_completeness(self): return self._avg(lambda r: r.quality_report.get("completeness", 0))
    @property
    def avg_accuracy(self): return self._avg(lambda r: r.quality_report.get("accuracy_confidence", 0))
    @property
    def avg_layout_fidelity(self): return self._avg(lambda r: r.quality_report.get("layout_fidelity", 0))
    @property
    def avg_f1(self): return self._avg(lambda r: r.metrics.get("f1", 0))
    @property
    def avg_exact_match(self): return self._avg(lambda r: r.metrics.get("exact_match_rate", 0))
    @property
    def pass_rate(self):
        return round(sum(1 for r in self.results if r.score.get("passed")) / max(self.total, 1), 4)
    @property
    def avg_processing_ms(self): return int(self._avg(lambda r: r.processing_time_ms))
    @property
    def accept_count(self): return sum(1 for r in self.results if r.quality_report.get("recommendation") == "accept")
    @property
    def review_count(self): return sum(1 for r in self.results if r.quality_report.get("recommendation") == "human_review")
    @property
    def reprocess_count(self): return sum(1 for r in self.results if r.quality_report.get("recommendation") == "reprocess")
    @property
    def hallucination_count(self): return sum(len(r.grounding_report.get("flagged_hallucinations", [])) for r in self.results)

    def by_doc_type(self) -> dict[str, dict]:
        groups: dict[str, list] = {}
        for r in self.results:
            groups.setdefault(r.doc_type, []).append(r)
        out = {}
        for dt, rs in groups.items():
            sub = AggregateStats(rs)
            out[dt] = {"count": sub.total, "avg_quality": sub.avg_quality_score,
                       "avg_grounding": sub.avg_grounding_rate, "avg_f1": sub.avg_f1, "pass_rate": sub.pass_rate}
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_documents": self.total,
            "avg_quality_score": self.avg_quality_score,
            "avg_grounding_rate": self.avg_grounding_rate,
            "avg_completeness": self.avg_completeness,
            "avg_accuracy": self.avg_accuracy,
            "avg_layout_fidelity": self.avg_layout_fidelity,
            "avg_f1": self.avg_f1,
            "avg_exact_match": self.avg_exact_match,
            "pass_rate": self.pass_rate,
            "avg_processing_ms": self.avg_processing_ms,
            "accept_count": self.accept_count,
            "review_count": self.review_count,
            "reprocess_count": self.reprocess_count,
            "hallucination_count": self.hallucination_count,
            "by_doc_type": self.by_doc_type(),
            "results": [r.to_dict() for r in self.results],
        }


async def run_benchmark(
    benchmark: dict,
    noise_config: NoiseConfig | None = None,
) -> PipelineResult:
    start = time.monotonic()
    doc_id = benchmark["document_id"]

    text = benchmark["text"]
    if noise_config:
        seed = hash(f"{doc_id}_pipeline_noise") & 0xFFFFFFFF
        text = inject_ocr_noise(text, noise_config, seed=seed)

    doc_tree = DocumentTree(
        document_id=doc_id,
        pages=[Page(page_number=1, regions=[
            Region(id=f"r_{doc_id}_0", type="TEXT", content=text, confidence=1.0),
        ])],
        source_format="benchmark", text_layer_present=True,
    )

    state = AgentState(
        document_id=doc_id, job_id=f"bench_{uuid.uuid4().hex[:12]}",
        source_filename=benchmark.get("filename", "benchmark.pdf"),
        document_tree=dict(doc_tree),
        extraction_schema={
            "schema_id": f"schema_{doc_id}", "doc_type": benchmark.get("doc_type", "document"),
            "version": "1.0", "nodes": benchmark.get("schema_nodes", []),
        },
    )

    for agent_cls in [ClassifierAgent, RouterAgent]:
        agent = agent_cls() if agent_cls != ClassifierAgent else agent_cls()
        state = await agent.run(state)

    extractor, validator, scorer = ExtractorAgent(), ValidatorAgent(), ScorerAgent()
    max_rounds = state.get("max_correction_rounds", 3)
    for rnd in range(max_rounds):
        state["correction_round"] = rnd
        state = await extractor.run(state)
        state = await validator.run(state)
        state = await scorer.run(state)
        if state.get("recommendation") == "accept":
            break

    extraction = state.get("extraction_result", {})
    grounding = GroundingVerifier().verify(extraction, dict(doc_tree), doc_id)
    metrics = compute_metrics(extraction, benchmark["expected"], document_id=doc_id)
    score = score_fn(metrics, threshold=0.70)

    return PipelineResult(
        document_id=doc_id, doc_type=benchmark.get("doc_type", "unknown"),
        extraction=extraction, expected=benchmark["expected"],
        quality_report=state.get("quality_report", {}),
        grounding_report=dict(grounding),
        metrics=metrics, score=score,
        verification_report=state.get("verification_report", {}),
        processing_time_ms=int((time.monotonic() - start) * 1000),
        correction_rounds=state.get("correction_round", 0) + 1,
    )


async def run_all_benchmarks(
    benchmarks: list[dict] | None = None,
    noise_config: NoiseConfig | None = None,
) -> AggregateStats:
    if benchmarks is None:
        from pixora.evals.benchmarks.golden_data import GOLDEN_BENCHMARKS
        benchmarks = GOLDEN_BENCHMARKS
    results = [await run_benchmark(b, noise_config=noise_config) for b in benchmarks]
    return AggregateStats(results)
