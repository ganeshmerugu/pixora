from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.metrics import compute_eval_metrics, EvalMetrics
from pixora.evals.scoring import score_eval, EvalScore
from pixora.evals.calibration import CalibrationReport, compute_calibration
from pixora.evals.table_eval import TableEvalMetrics, match_line_items
from pixora.evals.cost_eval import CostEfficiencyReport, evaluate_cost_efficiency
from pixora.evals.dedup_eval import DedupEvalResult, evaluate_dedup
from pixora.evals.perf import PerfBenchmarkResult


class BenchmarkCase(TypedDict, total=False):
    document_id: Required[str]
    expected: Required[dict[str, Any]]
    doc_type: str
    description: str
    metadata: dict[str, Any]


class EvalResult(TypedDict, total=False):
    document_id: Required[str]
    metrics: Required[EvalMetrics]
    score: Required[EvalScore]
    table_metrics: TableEvalMetrics
    calibration: CalibrationReport


class EvalSuiteReport(TypedDict, total=False):
    suite_name: str
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    avg_f1: float
    avg_score: float
    avg_table_f1: float
    avg_calibration_ece: float
    avg_layout_accuracy: float
    results: list[EvalResult]
    perf: PerfBenchmarkResult
    cost_efficiency: CostEfficiencyReport
    dedup: DedupEvalResult
    metadata: dict[str, Any]


class EvalRunner:
    def __init__(
        self,
        threshold: float = 0.80,
        enable_tables: bool = True,
        enable_calibration: bool = True,
        enable_dedup: bool = False,
    ):
        self.threshold = threshold
        self.enable_tables = enable_tables
        self.enable_calibration = enable_calibration
        self.enable_dedup = enable_dedup

    def run_suite(
        self,
        predictions: dict[str, dict[str, Any]],
        benchmarks: list[BenchmarkCase],
        suite_name: str = "default",
        confidence_data: dict[str, list[dict]] | None = None,
        predicted_trees: dict[str, dict] | None = None,
        expected_trees: dict[str, dict] | None = None,
        pipeline_results: list[dict] | None = None,
        dedup_documents: list[dict] | None = None,
        dedup_expected_pairs: list[tuple[str, str]] | None = None,
    ) -> EvalSuiteReport:
        results: list[EvalResult] = []
        all_calibration_preds: list[dict] = []
        table_f1_scores: list[float] = []
        layout_scores: list[float] = []

        for case in benchmarks:
            doc_id = case["document_id"]
            predicted = predictions.get(doc_id, {})
            expected = case["expected"]

            pred_tree = (predicted_trees or {}).get(doc_id)
            exp_tree = (expected_trees or {}).get(doc_id)

            metrics = compute_eval_metrics(
                predicted, expected, document_id=doc_id,
                predicted_tree=pred_tree, expected_tree=exp_tree,
            )
            score = score_eval(metrics, threshold=self.threshold)

            result = EvalResult(
                document_id=doc_id,
                metrics=metrics,
                score=score,
            )

            if self.enable_tables:
                pred_items = predicted.get("__line_items", [])
                exp_items = expected.get("__line_items", [])
                if pred_items or exp_items:
                    table_m = match_line_items(pred_items, exp_items, table_id=doc_id)
                    result["table_metrics"] = table_m
                    table_f1_scores.append(table_m["row_f1"])
                    metrics["table_f1"] = table_m["row_f1"]

            if self.enable_calibration and confidence_data:
                doc_conf = confidence_data.get(doc_id, [])
                if doc_conf:
                    all_calibration_preds.extend(doc_conf)
                    doc_cal = compute_calibration(doc_conf)
                    result["calibration"] = doc_cal

            layout_scores.append(metrics.get("layout_accuracy", 1.0))
            results.append(result)

        passed = sum(1 for r in results if r["score"]["passed"])
        failed = len(results) - passed
        f1_scores = [r["metrics"]["f1"] for r in results]
        w_scores = [r["score"]["weighted_score"] for r in results]

        report = EvalSuiteReport(
            suite_name=suite_name,
            total_cases=len(results),
            passed=passed,
            failed=failed,
            pass_rate=round(passed / max(len(results), 1), 4),
            avg_f1=round(sum(f1_scores) / max(len(f1_scores), 1), 4),
            avg_score=round(sum(w_scores) / max(len(w_scores), 1), 4),
            results=results,
        )

        if table_f1_scores:
            report["avg_table_f1"] = round(
                sum(table_f1_scores) / len(table_f1_scores), 4
            )

        if layout_scores:
            report["avg_layout_accuracy"] = round(
                sum(layout_scores) / len(layout_scores), 4
            )

        if self.enable_calibration and all_calibration_preds:
            suite_cal = compute_calibration(all_calibration_preds)
            report["avg_calibration_ece"] = suite_cal["ece"]

        if pipeline_results:
            report["cost_efficiency"] = evaluate_cost_efficiency(pipeline_results)

        if self.enable_dedup and dedup_documents and dedup_expected_pairs:
            report["dedup"] = evaluate_dedup(
                dedup_documents, dedup_expected_pairs,
            )

        return report
