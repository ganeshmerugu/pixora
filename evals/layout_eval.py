from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class LayoutEvalResult(TypedDict, total=False):
    layout_accuracy: Required[float]
    region_detection_f1: float
    reading_order_kendall_tau: float
    bbox_iou_mean: float
    region_matches: list[dict[str, Any]]
    unmatched_predicted: int
    unmatched_expected: int
    metadata: dict[str, Any]


LAYOUT_WEIGHTS = {
    "region_f1": 0.4,
    "reading_order": 0.3,
    "bbox_iou": 0.3,
}

IOU_MATCH_THRESHOLD = 0.5


def compute_bbox_iou(a: dict, b: dict) -> float:
    ax1 = a.get("x", 0)
    ay1 = a.get("y", 0)
    ax2 = ax1 + a.get("width", 0)
    ay2 = ay1 + a.get("height", 0)

    bx1 = b.get("x", 0)
    by1 = b.get("y", 0)
    bx2 = bx1 + b.get("width", 0)
    by2 = by1 + b.get("height", 0)

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0
    return round(inter_area / union_area, 4)


def _extract_regions(tree: dict) -> list[dict]:
    regions: list[dict] = []
    for page in tree.get("pages", []):
        for region in page.get("regions", []):
            regions.append(region)
    return regions


def _match_regions(
    predicted: list[dict],
    expected: list[dict],
) -> list[tuple[int, int, float]]:
    candidates: list[tuple[float, int, int]] = []
    for pi, pr in enumerate(predicted):
        for ei, er in enumerate(expected):
            p_type = pr.get("type", "").lower()
            e_type = er.get("type", "").lower()
            if p_type != e_type:
                continue
            p_bbox = pr.get("bbox", {})
            e_bbox = er.get("bbox", {})
            if not p_bbox or not e_bbox:
                continue
            iou = compute_bbox_iou(p_bbox, e_bbox)
            if iou >= IOU_MATCH_THRESHOLD:
                candidates.append((iou, pi, ei))

    candidates.sort(key=lambda x: -x[0])
    used_pred: set[int] = set()
    used_exp: set[int] = set()
    matches: list[tuple[int, int, float]] = []

    for iou, pi, ei in candidates:
        if pi in used_pred or ei in used_exp:
            continue
        matches.append((pi, ei, iou))
        used_pred.add(pi)
        used_exp.add(ei)

    return matches


def _kendall_tau_normalized(pairs: list[tuple[int, int]]) -> float:
    if len(pairs) < 2:
        return 1.0
    sorted_by_exp = sorted(pairs, key=lambda x: x[1])
    pred_order = [p[0] for p in sorted_by_exp]
    n = len(pred_order)
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pred_order[i] < pred_order[j]:
                concordant += 1
            elif pred_order[i] > pred_order[j]:
                discordant += 1
    total = concordant + discordant
    if total == 0:
        return 1.0
    tau = (concordant - discordant) / total
    return round((tau + 1.0) / 2.0, 4)


def compute_layout_accuracy(
    predicted_tree: dict,
    expected_tree: dict,
) -> LayoutEvalResult:
    pred_regions = _extract_regions(predicted_tree)
    exp_regions = _extract_regions(expected_tree)

    if not pred_regions and not exp_regions:
        return LayoutEvalResult(
            layout_accuracy=1.0, region_detection_f1=1.0,
            reading_order_kendall_tau=1.0, bbox_iou_mean=1.0,
            region_matches=[], unmatched_predicted=0, unmatched_expected=0,
        )

    if not pred_regions or not exp_regions:
        return LayoutEvalResult(
            layout_accuracy=0.0, region_detection_f1=0.0,
            reading_order_kendall_tau=0.0, bbox_iou_mean=0.0,
            region_matches=[],
            unmatched_predicted=len(pred_regions),
            unmatched_expected=len(exp_regions),
        )

    matches = _match_regions(pred_regions, exp_regions)
    tp = len(matches)
    precision = tp / len(pred_regions) if pred_regions else 0.0
    recall = tp / len(exp_regions) if exp_regions else 0.0
    region_f1 = (
        round(2 * precision * recall / (precision + recall), 4)
        if (precision + recall) > 0 else 0.0
    )

    iou_values = [iou for _, _, iou in matches]
    bbox_iou_mean = round(sum(iou_values) / len(iou_values), 4) if iou_values else 0.0

    reading_order_pairs: list[tuple[int, int]] = []
    for pi, ei, _ in matches:
        p_order = pred_regions[pi].get("reading_order", pi)
        e_order = exp_regions[ei].get("reading_order", ei)
        reading_order_pairs.append((p_order, e_order))
    reading_order_tau = _kendall_tau_normalized(reading_order_pairs)

    w = LAYOUT_WEIGHTS
    layout_accuracy = round(
        w["region_f1"] * region_f1
        + w["reading_order"] * reading_order_tau
        + w["bbox_iou"] * bbox_iou_mean,
        4,
    )

    region_match_details = [
        {
            "predicted_idx": pi,
            "expected_idx": ei,
            "iou": iou,
            "type": pred_regions[pi].get("type", ""),
        }
        for pi, ei, iou in matches
    ]

    return LayoutEvalResult(
        layout_accuracy=layout_accuracy,
        region_detection_f1=region_f1,
        reading_order_kendall_tau=reading_order_tau,
        bbox_iou_mean=bbox_iou_mean,
        region_matches=region_match_details,
        unmatched_predicted=len(pred_regions) - tp,
        unmatched_expected=len(exp_regions) - tp,
    )
