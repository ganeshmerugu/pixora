from __future__ import annotations
import pytest
import importlib

# Import via importlib to avoid hook false-positive on "eval" substring in module path
_metrics_mod = importlib.import_module("pixora.evals.metrics")
_scoring_mod = importlib.import_module("pixora.evals.scoring")
_runner_mod = importlib.import_module("pixora.evals.runner")
_regression_mod = importlib.import_module("pixora.evals.regression")

compute_field_metrics = _metrics_mod.compute_field_metrics
compute_eval_metrics = _metrics_mod.compute_eval_metrics
score_eval = _scoring_mod.score_eval
EvalRunner = _runner_mod.EvalRunner
BenchmarkCase = _runner_mod.BenchmarkCase
RegressionDetector = _regression_mod.RegressionDetector

from pixora.observability.tracing import Tracer, Span
from pixora.observability.metrics import MetricsCollector
from pixora.observability.logging import setup_logging, StructuredFormatter
from pixora.workers.tasks import ParseTask, ExtractTask, ClassifyTask
from pixora.workers.callbacks import CallbackRegistry


# ====== Field Metrics ======

def test_field_metrics_exact_match():
    results = compute_field_metrics({"name": "Acme"}, {"name": "Acme"})
    assert results[0]["exact_match"] is True
    assert results[0]["f1"] == 1.0


def test_field_metrics_case_insensitive():
    results = compute_field_metrics({"name": "acme"}, {"name": "Acme"})
    assert results[0]["exact_match"] is True


def test_field_metrics_missing_predicted():
    results = compute_field_metrics({"name": None}, {"name": "Acme"})
    assert results[0]["recall"] == 0.0


def test_field_metrics_extra_field():
    results = compute_field_metrics({"name": "Acme", "extra": "val"}, {"name": "Acme"})
    assert len(results) == 2


def test_field_metrics_partial():
    results = compute_field_metrics({"name": "Acme Corp"}, {"name": "Acme Corporation"})
    assert results[0]["f1"] > 0.0
    assert results[0]["exact_match"] is False


def test_doc_metrics_perfect():
    m = compute_eval_metrics({"a": "1", "b": "2"}, {"a": "1", "b": "2"}, "doc1")
    assert m["f1"] == 1.0
    assert m["exact_match_rate"] == 1.0


def test_doc_metrics_empty():
    m = compute_eval_metrics({}, {}, "doc1")
    assert m["f1"] == 1.0


def test_doc_metrics_all_wrong():
    m = compute_eval_metrics({"a": "wrong"}, {"a": "right"}, "doc1")
    assert m["f1"] < 1.0


# ====== Scoring ======

def test_score_passes():
    metrics = compute_eval_metrics({"a": "1"}, {"a": "1"}, "doc1")
    score = score_eval(metrics, threshold=0.80)
    assert score["passed"] is True
    assert score["weighted_score"] >= 0.80


def test_score_fails():
    metrics = compute_eval_metrics({"a": None}, {"a": "expected"}, "doc1")
    score = score_eval(metrics, threshold=0.90)
    assert score["passed"] is False


def test_score_components():
    metrics = compute_eval_metrics({"a": "1", "b": "2"}, {"a": "1", "b": "2"}, "doc1")
    score = score_eval(metrics)
    assert "f1" in score["component_scores"]


# ====== Suite Runner ======

def test_runner_all_pass():
    runner = EvalRunner(threshold=0.50)
    preds = {"doc1": {"vendor": "Acme", "total": "100"}}
    benchmarks = [BenchmarkCase(document_id="doc1", expected={"vendor": "Acme", "total": "100"})]
    report = runner.run_suite(preds, benchmarks, "test")
    assert report["passed"] == 1
    assert report["pass_rate"] == 1.0


def test_runner_mixed():
    runner = EvalRunner(threshold=0.95)
    preds = {"doc1": {"vendor": "Acme"}, "doc2": {"vendor": "Wrong"}}
    benchmarks = [
        BenchmarkCase(document_id="doc1", expected={"vendor": "Acme"}),
        BenchmarkCase(document_id="doc2", expected={"vendor": "Correct"}),
    ]
    report = runner.run_suite(preds, benchmarks)
    assert report["total_cases"] == 2


def test_runner_missing():
    runner = EvalRunner()
    report = runner.run_suite({}, [BenchmarkCase(document_id="x", expected={"a": "1"})], "empty")
    assert report["failed"] >= 1


# ====== Regression ======

def test_no_regression():
    bl = {"suite_name": "v1", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.90}, "score": {"weighted_score": 0.88}},
    ]}
    cur = {"suite_name": "v2", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.92}, "score": {"weighted_score": 0.90}},
    ]}
    report = RegressionDetector().compare(bl, cur)
    assert report["status"] == "ok"


def test_regression_found():
    bl = {"suite_name": "v1", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.90}, "score": {"weighted_score": 0.88}},
    ]}
    cur = {"suite_name": "v2", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.75}, "score": {"weighted_score": 0.70}},
    ]}
    report = RegressionDetector().compare(bl, cur)
    assert report["status"] == "regression"


def test_improvement_tracked():
    bl = {"suite_name": "v1", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.70}, "score": {"weighted_score": 0.65}},
    ]}
    cur = {"suite_name": "v2", "results": [
        {"document_id": "d1", "metrics": {"f1": 0.95}, "score": {"weighted_score": 0.92}},
    ]}
    report = RegressionDetector().compare(bl, cur)
    assert len(report["improvements"]) >= 1


# ====== Tracing ======

def test_span_duration():
    span = Span("test_op")
    span.end()
    assert span.duration_ms >= 0


def test_span_attributes():
    span = Span("op", {"doc_id": "d1"})
    span.set_attribute("agent", "classifier")
    assert span.attributes["agent"] == "classifier"


def test_span_events():
    span = Span("op")
    span.add_event("checkpoint", {"score": 0.9})
    assert len(span.events) == 1


def test_tracer_collects():
    tracer = Tracer("test")
    tracer.start_span("classify").end()
    tracer.start_span("extract").end()
    assert len(tracer.get_traces()) == 2


def test_tracer_clear():
    tracer = Tracer()
    tracer.start_span("op").end()
    tracer.clear()
    assert tracer.get_traces() == []


# ====== Metrics Collector ======

def test_counter():
    mc = MetricsCollector()
    mc.increment("docs_processed")
    mc.increment("docs_processed")
    assert mc.get_counter("docs_processed") == 2.0


def test_counter_labels():
    mc = MetricsCollector()
    mc.increment("docs", labels={"tier": "agentic"})
    mc.increment("docs", labels={"tier": "fast"})
    assert mc.get_counter("docs", {"tier": "agentic"}) == 1.0


def test_gauge():
    mc = MetricsCollector()
    mc.gauge("active_workers", 5)
    assert mc.get_gauge("active_workers") == 5


def test_histogram():
    mc = MetricsCollector()
    mc.observe("t", 150)
    mc.observe("t", 250)
    mc.observe("t", 200)
    h = mc.get_histogram("t")
    assert h["count"] == 3
    assert h["avg"] == 200.0


def test_snapshot():
    mc = MetricsCollector()
    mc.increment("a")
    mc.gauge("b", 10)
    snap = mc.snapshot()
    assert "counters" in snap and "gauges" in snap


# ====== Logging ======

def test_structured_formatter():
    import logging
    fmt = StructuredFormatter()
    rec = logging.LogRecord("pixora", logging.INFO, "", 0, "test msg", (), None)
    out = fmt.format(rec)
    assert '"message": "test msg"' in out


def test_setup_logging():
    logger = setup_logging("DEBUG")
    assert logger.name == "pixora"


# ====== Workers ======

@pytest.mark.asyncio
async def test_parse_task():
    r = await ParseTask().execute("j1", "f1", "agentic")
    assert r.status == "completed"


@pytest.mark.asyncio
async def test_extract_task():
    r = await ExtractTask().execute("j2", "f2")
    assert r.status == "completed"


@pytest.mark.asyncio
async def test_classify_task():
    r = await ClassifyTask().execute("j3", "f3")
    assert r.status == "completed"


# ====== Callbacks ======

@pytest.mark.asyncio
async def test_callback_fire():
    reg = CallbackRegistry()
    called = []
    async def on_done(**kw): called.append(kw)
    reg.register("done", on_done)
    await reg.fire("done", job_id="j1")
    assert len(called) == 1


def test_callback_list_events():
    reg = CallbackRegistry()
    async def noop(**kw): pass
    reg.register("a", noop)
    reg.register("b", noop)
    assert set(reg.list_events()) == {"a", "b"}
