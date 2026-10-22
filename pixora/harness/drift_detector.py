from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class DriftAlert(TypedDict, total=False):
    metric: Required[str]
    level: Required[str]
    current_value: float
    baseline_value: float
    delta: float
    threshold: float


class DriftReport(TypedDict, total=False):
    batch_id: str
    document_count: int
    alerts: list[DriftAlert]
    metrics_summary: dict[str, float]
    status: str


MONITORS: dict[str, dict[str, float]] = {
    "grounding_rate":        {"warn": -0.03, "alert": -0.08},
    "completeness":          {"warn": -0.05, "alert": -0.10},
    "correction_rounds":     {"warn": 0.5,   "alert": 1.0},
    "cost_per_document":     {"warn": 0.20,  "alert": 0.50},
    "human_escalation_rate": {"warn": 0.05,  "alert": 0.10},
}


class DriftDetector:
    def __init__(self, baselines: dict[str, float] | None = None):
        self.baselines = baselines or {}

    def set_baseline(self, metric: str, value: float) -> None:
        self.baselines[metric] = value

    def set_baselines_from_batch(self, reports: list[dict]) -> None:
        if not reports:
            return
        metrics = self._aggregate_metrics(reports)
        for metric, value in metrics.items():
            self.baselines[metric] = value

    def detect(self, reports: list[dict], batch_id: str = "") -> DriftReport:
        if not reports:
            return DriftReport(batch_id=batch_id, document_count=0, alerts=[], metrics_summary={}, status="ok")

        current = self._aggregate_metrics(reports)
        alerts: list[DriftAlert] = []

        for metric, thresholds in MONITORS.items():
            baseline = self.baselines.get(metric)
            current_val = current.get(metric)
            if baseline is None or current_val is None:
                continue

            delta = current_val - baseline
            increasing_bad = metric in ("correction_rounds", "cost_per_document", "human_escalation_rate")

            if increasing_bad:
                if delta >= thresholds["alert"]:
                    alerts.append(DriftAlert(
                        metric=metric, level="alert", current_value=current_val,
                        baseline_value=baseline, delta=round(delta, 4), threshold=thresholds["alert"],
                    ))
                elif delta >= thresholds["warn"]:
                    alerts.append(DriftAlert(
                        metric=metric, level="warn", current_value=current_val,
                        baseline_value=baseline, delta=round(delta, 4), threshold=thresholds["warn"],
                    ))
            else:
                if delta <= thresholds["alert"]:
                    alerts.append(DriftAlert(
                        metric=metric, level="alert", current_value=current_val,
                        baseline_value=baseline, delta=round(delta, 4), threshold=thresholds["alert"],
                    ))
                elif delta <= thresholds["warn"]:
                    alerts.append(DriftAlert(
                        metric=metric, level="warn", current_value=current_val,
                        baseline_value=baseline, delta=round(delta, 4), threshold=thresholds["warn"],
                    ))

        has_alert = any(a["level"] == "alert" for a in alerts)
        has_warn = any(a["level"] == "warn" for a in alerts)
        status = "alert" if has_alert else "warn" if has_warn else "ok"

        return DriftReport(
            batch_id=batch_id,
            document_count=len(reports),
            alerts=alerts,
            metrics_summary=current,
            status=status,
        )

    def _aggregate_metrics(self, reports: list[dict]) -> dict[str, float]:
        n = len(reports)
        if n == 0:
            return {}

        totals: dict[str, float] = {}
        counts: dict[str, int] = {}

        for r in reports:
            qr = r.get("quality_report", r)
            for key in ("grounding_rate", "grounding_score", "completeness", "overall_score"):
                val = qr.get(key)
                if val is not None:
                    mapped = "grounding_rate" if key in ("grounding_rate", "grounding_score") else key
                    if mapped == key or key == "grounding_score":
                        mapped = "grounding_rate" if "grounding" in key else key
                    totals[mapped] = totals.get(mapped, 0.0) + float(val)
                    counts[mapped] = counts.get(mapped, 0) + 1

            rounds = r.get("correction_round", r.get("total_rounds"))
            if rounds is not None:
                totals["correction_rounds"] = totals.get("correction_rounds", 0.0) + float(rounds)
                counts["correction_rounds"] = counts.get("correction_rounds", 0) + 1

            rec = qr.get("recommendation", r.get("recommendation"))
            if rec == "human_review":
                totals["human_escalation_rate"] = totals.get("human_escalation_rate", 0.0) + 1.0
                counts["human_escalation_rate"] = counts.get("human_escalation_rate", 0) + 1
            elif rec is not None:
                counts.setdefault("human_escalation_rate", 0)
                counts["human_escalation_rate"] = counts.get("human_escalation_rate", 0) + 1

        result = {}
        for key in totals:
            c = counts.get(key, 1)
            result[key] = round(totals[key] / c, 4) if c > 0 else 0.0

        if "human_escalation_rate" in counts and counts["human_escalation_rate"] > 0:
            result["human_escalation_rate"] = round(totals.get("human_escalation_rate", 0.0) / n, 4)

        return result
