from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.matchers import composite_match, normalize_text
from pixora.evals.layout_eval import compute_layout_accuracy


class FieldMetrics(TypedDict, total=False):
    field: Required[str]
    precision: Required[float]
    recall: Required[float]
    f1: Required[float]
    exact_match: bool
    predicted: str | None
    expected: str | None
    match_method: str
    levenshtein_sim: float
    token_f1: float
    semantic_sim: float


class EvalMetrics(TypedDict, total=False):
    document_id: str
    precision: Required[float]
    recall: Required[float]
    f1: Required[float]
    exact_match_rate: float
    field_metrics: list[FieldMetrics]
    layout_accuracy: float
    table_f1: float
    calibration_ece: float
    calibration_ece_inv: float
    dedup_f1: float
    reading_order_score: float
    cross_page_table_score: float
    semantic_detection_f1: float
    match_method_distribution: dict[str, int]
    metadata: dict[str, Any]


def compute_field_metrics(predicted: dict[str, Any], expected: dict[str, Any]) -> list[FieldMetrics]:
    all_fields = set(predicted.keys()) | set(expected.keys())
    all_fields = {f for f in all_fields if not f.startswith("__")}
    results: list[FieldMetrics] = []

    for field in sorted(all_fields):
        pred_val = predicted.get(field)
        exp_val = expected.get(field)

        pred_present = pred_val is not None and str(pred_val).strip() != ""
        exp_present = exp_val is not None and str(exp_val).strip() != ""

        if pred_present and exp_present:
            p_str = str(pred_val)
            e_str = str(exp_val)
            exact = normalize_text(p_str) == normalize_text(e_str)
            if exact:
                precision = recall = f1 = 1.0
                match_result = composite_match(p_str, e_str)
            else:
                match_result = composite_match(p_str, e_str)
                precision = match_result["score"]
                recall = precision
                f1 = _f1(precision, recall)
        elif pred_present and not exp_present:
            precision, recall, f1, exact = 0.0, 1.0, 0.0, False
            match_result = None
        elif not pred_present and exp_present:
            precision, recall, f1, exact = 1.0, 0.0, 0.0, False
            match_result = None
        else:
            precision, recall, f1, exact = 1.0, 1.0, 1.0, True
            match_result = None

        fm = FieldMetrics(
            field=field,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            exact_match=exact,
            predicted=str(pred_val) if pred_val is not None else None,
            expected=str(exp_val) if exp_val is not None else None,
        )
        if match_result:
            fm["match_method"] = match_result.get("method", "composite")
            fm["levenshtein_sim"] = match_result.get("levenshtein_sim", 0.0)
            fm["token_f1"] = match_result.get("token_f1", 0.0)
            fm["semantic_sim"] = match_result.get("semantic_sim", 0.0)

        results.append(fm)

    return results


def compute_eval_metrics(
    predicted: dict[str, Any],
    expected: dict[str, Any],
    document_id: str = "",
    layout_accuracy: float | None = None,
    predicted_tree: dict | None = None,
    expected_tree: dict | None = None,
) -> EvalMetrics:
    field_metrics = compute_field_metrics(predicted, expected)

    if not field_metrics:
        la = layout_accuracy or 1.0
        if predicted_tree and expected_tree:
            layout_result = compute_layout_accuracy(predicted_tree, expected_tree)
            la = layout_result["layout_accuracy"]
        return EvalMetrics(
            document_id=document_id, precision=1.0, recall=1.0, f1=1.0,
            exact_match_rate=1.0, field_metrics=[], layout_accuracy=la,
        )

    precisions = [m["precision"] for m in field_metrics]
    recalls = [m["recall"] for m in field_metrics]
    exact_matches = [m["exact_match"] for m in field_metrics]

    avg_p = sum(precisions) / len(precisions)
    avg_r = sum(recalls) / len(recalls)
    avg_f1 = _f1(avg_p, avg_r)
    em_rate = sum(1 for e in exact_matches if e) / len(exact_matches)

    method_dist: dict[str, int] = {}
    for m in field_metrics:
        method = m.get("match_method", "none")
        method_dist[method] = method_dist.get(method, 0) + 1

    la = layout_accuracy or 1.0
    if predicted_tree and expected_tree:
        layout_result = compute_layout_accuracy(predicted_tree, expected_tree)
        la = layout_result["layout_accuracy"]

    return EvalMetrics(
        document_id=document_id,
        precision=round(avg_p, 4),
        recall=round(avg_r, 4),
        f1=round(avg_f1, 4),
        exact_match_rate=round(em_rate, 4),
        field_metrics=field_metrics,
        layout_accuracy=la,
        match_method_distribution=method_dist,
    )


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)
