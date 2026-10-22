from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class CalibrationBin(TypedDict, total=False):
    bin_lower: Required[float]
    bin_upper: Required[float]
    avg_confidence: Required[float]
    avg_accuracy: Required[float]
    count: Required[int]


class CalibrationReport(TypedDict, total=False):
    ece: Required[float]
    mce: Required[float]
    brier_score: Required[float]
    bins: Required[list[CalibrationBin]]
    total_predictions: int
    overconfidence_ratio: float
    underconfidence_ratio: float
    metadata: dict[str, Any]


def compute_calibration(
    predictions: list[dict],
    n_bins: int = 10,
) -> CalibrationReport:
    if not predictions:
        return CalibrationReport(
            ece=0.0, mce=0.0, brier_score=0.0, bins=[],
            total_predictions=0, overconfidence_ratio=0.0, underconfidence_ratio=0.0,
        )

    bin_width = 1.0 / n_bins
    bin_confs: list[list[float]] = [[] for _ in range(n_bins)]
    bin_corrects: list[list[float]] = [[] for _ in range(n_bins)]

    brier_sum = 0.0
    overconfident = 0
    underconfident = 0
    total = len(predictions)

    for pred in predictions:
        conf = float(pred.get("confidence", 0.0))
        correct = 1.0 if pred.get("correct", False) else 0.0

        brier_sum += (conf - correct) ** 2

        bin_idx = min(int(conf / bin_width), n_bins - 1)
        bin_confs[bin_idx].append(conf)
        bin_corrects[bin_idx].append(correct)

    bins: list[CalibrationBin] = []
    ece = 0.0
    mce = 0.0

    for i in range(n_bins):
        lower = round(i * bin_width, 4)
        upper = round((i + 1) * bin_width, 4)
        count = len(bin_confs[i])
        if count == 0:
            bins.append(CalibrationBin(
                bin_lower=lower, bin_upper=upper,
                avg_confidence=0.0, avg_accuracy=0.0, count=0,
            ))
            continue

        avg_conf = sum(bin_confs[i]) / count
        avg_acc = sum(bin_corrects[i]) / count
        gap = abs(avg_acc - avg_conf)

        ece += (count / total) * gap
        mce = max(mce, gap)

        if avg_conf > avg_acc:
            overconfident += count
        elif avg_conf < avg_acc:
            underconfident += count

        bins.append(CalibrationBin(
            bin_lower=lower, bin_upper=upper,
            avg_confidence=round(avg_conf, 4),
            avg_accuracy=round(avg_acc, 4),
            count=count,
        ))

    return CalibrationReport(
        ece=round(ece, 4),
        mce=round(mce, 4),
        brier_score=round(brier_sum / total, 4),
        bins=bins,
        total_predictions=total,
        overconfidence_ratio=round(overconfident / total, 4) if total else 0.0,
        underconfidence_ratio=round(underconfident / total, 4) if total else 0.0,
    )


def build_reliability_diagram_data(report: CalibrationReport) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for b in report.get("bins", []):
        if b["count"] > 0:
            midpoint = round((b["bin_lower"] + b["bin_upper"]) / 2, 4)
            points.append({
                "x": midpoint,
                "y": b["avg_accuracy"],
                "confidence": b["avg_confidence"],
                "count": float(b["count"]),
                "gap": round(abs(b["avg_accuracy"] - b["avg_confidence"]), 4),
            })
    return points
