from __future__ import annotations
import pytest
from pixora.evals.metrics import compute_field_metrics, compute_eval_metrics
from pixora.evals.scoring import score_eval
from pixora.evals.runner import EvalRunner, BenchmarkCase
from pixora.evals.regression import RegressionDetector


# --- Metrics ---

def test_field_metrics_exact_match():
    results = compute_field_metrics({"name": "Acme"}, {"name": "Acme"})
    assert len(results) == 1
    assert results[0]["exact_match"] is True
    assert results[0]["f1"] == 1.0


def test_field_metrics_case_mismatch():
    results = compute_field_metrics({"name": "acme"}, {"name": "Acme"})
    assert results[0]["exact_match"] is True  # normalized comparison


def test_field_metrics_missing_predicted():
    results = compute_field_metrics({"name": None}, {"name": "Acme"})
    assert results[0]["recall"] == 0.0


def test_field_metrics_extra_predicted():
    results = compute_field_metrics({"name": "Acme", "extra": "val"}, {"name": "Acme"})
    assert len(results) == 2


def test_field_metrics_partial_match():
    results = compute_field_metrics({"name": "Acme Corp"}, {"name": "Acme Corporation"})
    assert results[0]["f1"] > 0.0
    assert results[0]["exact_match"] is False


def test_metrics_perfect():
    m = compute_eval_metrics({"a": "1", "b": "2"}, {"a": "1", "b": "2"}, "doc1")
    assert m["f1"] == 1.0
    assert m["exact_match_rate"] == 1.0


def test_metrics_empty():
    m = compute_eval_metrics({}, {}, "doc1")
    assert m["f1"] == 1.0


def test_metrics_all_wrong():
    m = compute_eval_metrics({"a": "wrong"}, {"a": "right"}, "doc1")
    assert m["f1"] < 1.0


# --- Scoring ---

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
    assert "precision" in score["component_scores"]


# --- Runner ---

def test_runner_all_pass():
    runner = EvalRunner(threshold=0.50)
    predictions = {"doc1": {"vendor": "Acme", "total": "100"}}
    benchmarks = [BenchmarkCase(document_id="doc1", expected={"vendor": "Acme", "total": "100"})]
    report = runner.run_suite(predictions, benchmarks, "test_suite")
    assert report["passed"] == 1
    assert report["failed"] == 0
    assert report["pass_rate"] == 1.0


def test_runner_mixed_results():
    runner = EvalRunner(threshold=0.95)
    predictions = {
        "doc1": {"vendor": "Acme", "total": "100"},
        "doc2": {"vendor": "Wrong", "total": None},
    }
    benchmarks = [
        BenchmarkCase(document_id="doc1", expected={"vendor": "Acme", "total": "100"}),
        BenchmarkCase(document_id="doc2", expected={"vendor": "Correct", "total": "200"}),
    ]
    report = runner.run_suite(predictions, benchmarks, "mixed")
    assert report["total_cases"] == 2
    assert report["passed"] >= 1


def test_runner_missing_prediction():
    runner = EvalRunner()
    benchmarks = [BenchmarkCase(document_id="missing", expected={"a": "1"})]
    report = runner.run_suite({}, benchmarks, "empty")
    assert report["total_cases"] == 1
    assert report["failed"] >= 1


# --- Regression ---

def test_regression_none_detected():
    baseline_results = [{"document_id": "d1", "metrics": {"f1": 0.90, "exact_match_rate": 0.80}, "score": {"weighted_score": 0.88}}]
    current_results = [{"document_id": "d1", "metrics": {"f1": 0.92, "exact_match_rate": 0.85}, "score": {"weighted_score": 0.90}}]
    baseline = {"suite_name": "v1", "results": baseline_results}
    current = {"suite_name": "v2", "results": current_results}
    detector = RegressionDetector()
    report = detector.compare(baseline, current)
    assert report["status"] == "ok"
    assert len(report["regressions"]) == 0


def test_regression_detected():
    baseline_results = [{"document_id": "d1", "metrics": {"f1": 0.90, "exact_match_rate": 0.80}, "score": {"weighted_score": 0.88}}]
    current_results = [{"document_id": "d1", "metrics": {"f1": 0.75, "exact_match_rate": 0.60}, "score": {"weighted_score": 0.70}}]
    baseline = {"suite_name": "v1", "results": baseline_results}
    current = {"suite_name": "v2", "results": current_results}
    detector = RegressionDetector()
    report = detector.compare(baseline, current)
    assert report["status"] == "regression"
    assert len(report["regressions"]) >= 1


def test_regression_improvements_tracked():
    baseline_results = [{"document_id": "d1", "metrics": {"f1": 0.70}, "score": {"weighted_score": 0.65}}]
    current_results = [{"document_id": "d1", "metrics": {"f1": 0.95}, "score": {"weighted_score": 0.92}}]
    baseline = {"suite_name": "v1", "results": baseline_results}
    current = {"suite_name": "v2", "results": current_results}
    detector = RegressionDetector()
    report = detector.compare(baseline, current)
    assert len(report["improvements"]) >= 1
