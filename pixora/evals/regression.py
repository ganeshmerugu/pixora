from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.runner import EvalSuiteReport


class RegressionAlert(TypedDict, total=False):
    document_id: Required[str]
    metric: Required[str]
    baseline_value: float
    current_value: float
    delta: float
    severity: str


class RegressionReport(TypedDict, total=False):
    baseline_suite: str
    current_suite: str
    total_cases: int
    regressions: list[RegressionAlert]
    improvements: list[dict[str, Any]]
    status: str


REGRESSION_THRESHOLDS: dict[str, float] = {
    "f1": -0.05,
    "weighted_score": -0.05,
    "exact_match_rate": -0.10,
}


class RegressionDetector:
    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresholds = thresholds or REGRESSION_THRESHOLDS

    def compare(
        self,
        baseline: EvalSuiteReport,
        current: EvalSuiteReport,
    ) -> RegressionReport:
        baseline_map: dict[str, dict] = {}
        for r in baseline.get("results", []):
            baseline_map[r["document_id"]] = r

        regressions: list[RegressionAlert] = []
        improvements: list[dict[str, Any]] = []

        for result in current.get("results", []):
            doc_id = result["document_id"]
            base = baseline_map.get(doc_id)
            if not base:
                continue

            for metric, threshold in self.thresholds.items():
                cur_val = self._get_metric(result, metric)
                base_val = self._get_metric(base, metric)
                if cur_val is None or base_val is None:
                    continue

                delta = cur_val - base_val

                if delta < threshold:
                    regressions.append(RegressionAlert(
                        document_id=doc_id,
                        metric=metric,
                        baseline_value=round(base_val, 4),
                        current_value=round(cur_val, 4),
                        delta=round(delta, 4),
                        severity="critical" if delta < threshold * 2 else "warning",
                    ))
                elif delta > abs(threshold):
                    improvements.append({
                        "document_id": doc_id,
                        "metric": metric,
                        "delta": round(delta, 4),
                    })

        status = "regression" if regressions else "ok"

        return RegressionReport(
            baseline_suite=baseline.get("suite_name", ""),
            current_suite=current.get("suite_name", ""),
            total_cases=len(current.get("results", [])),
            regressions=regressions,
            improvements=improvements,
            status=status,
        )

    def _get_metric(self, result: dict, metric: str) -> float | None:
        if metric in ("f1", "exact_match_rate", "precision", "recall"):
            return result.get("metrics", {}).get(metric)
        if metric == "weighted_score":
            return result.get("score", {}).get("weighted_score")
        return None
