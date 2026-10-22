"""Layout detection metrics — mAP (mean Average Precision) and IoU.

Measures how accurately bounding boxes are placed around headers, paragraphs,
charts, tables, and captions.
"""
from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class DetectionBox(TypedDict, total=False):
    x: Required[float]
    y: Required[float]
    width: Required[float]
    height: Required[float]
    label: Required[str]
    confidence: float


class LayoutMetricsReport(TypedDict, total=False):
    mAP: Required[float]
    mAP_50: float
    mAP_75: float
    avg_iou: float
    per_class_ap: dict[str, float]
    per_class_count: dict[str, int]
    total_gt: int
    total_pred: int
    true_positives: int
    false_positives: int
    false_negatives: int
    metadata: dict[str, Any]


def compute_iou(a: DetectionBox, b: DetectionBox) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["width"], by1 + b["height"]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter_area

    return round(inter_area / union, 4) if union > 0 else 0.0


def _compute_ap_at_threshold(
    gt_boxes: list[DetectionBox],
    pred_boxes: list[DetectionBox],
    iou_threshold: float,
) -> tuple[float, int, int, int, list[float]]:
    if not gt_boxes:
        return (1.0, 0, len(pred_boxes), 0, []) if not pred_boxes else (0.0, 0, len(pred_boxes), 0, [])

    preds_sorted = sorted(pred_boxes, key=lambda p: p.get("confidence", 0.5), reverse=True)
    matched_gt: set[int] = set()
    tp = 0
    fp = 0
    ious: list[float] = []

    for pred in preds_sorted:
        best_iou = 0.0
        best_gi = -1
        for gi, gt in enumerate(gt_boxes):
            if gi in matched_gt:
                continue
            if gt["label"] != pred["label"]:
                continue
            iou = compute_iou(gt, pred)
            if iou > best_iou:
                best_iou = iou
                best_gi = gi

        if best_iou >= iou_threshold and best_gi >= 0:
            tp += 1
            matched_gt.add(best_gi)
            ious.append(best_iou)
        else:
            fp += 1

    fn = len(gt_boxes) - len(matched_gt)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    ap = precision * recall if (precision + recall) > 0 else 0.0

    return ap, tp, fp, fn, ious


def compute_layout_metrics(
    gt_pages: list[list[DetectionBox]],
    pred_pages: list[list[DetectionBox]],
) -> LayoutMetricsReport:
    all_gt: list[DetectionBox] = []
    all_pred: list[DetectionBox] = []
    for g, p in zip(gt_pages, pred_pages):
        all_gt.extend(g)
        all_pred.extend(p)

    classes = set(b["label"] for b in all_gt) | set(b["label"] for b in all_pred)

    per_class_ap: dict[str, float] = {}
    per_class_count: dict[str, int] = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0
    all_ious: list[float] = []

    for cls in classes:
        cls_gt = [b for b in all_gt if b["label"] == cls]
        cls_pred = [b for b in all_pred if b["label"] == cls]
        per_class_count[cls] = len(cls_gt)

        ap, tp, fp, fn, ious = _compute_ap_at_threshold(cls_gt, cls_pred, 0.5)
        per_class_ap[cls] = round(ap, 4)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        all_ious.extend(ious)

    mAP_50 = sum(per_class_ap.values()) / len(per_class_ap) if per_class_ap else 0.0

    ap_75_results: dict[str, float] = {}
    for cls in classes:
        cls_gt = [b for b in all_gt if b["label"] == cls]
        cls_pred = [b for b in all_pred if b["label"] == cls]
        ap75, *_ = _compute_ap_at_threshold(cls_gt, cls_pred, 0.75)
        ap_75_results[cls] = ap75
    mAP_75 = sum(ap_75_results.values()) / len(ap_75_results) if ap_75_results else 0.0

    thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    coco_aps: list[float] = []
    for t in thresholds:
        t_aps: list[float] = []
        for cls in classes:
            cls_gt = [b for b in all_gt if b["label"] == cls]
            cls_pred = [b for b in all_pred if b["label"] == cls]
            ap, *_ = _compute_ap_at_threshold(cls_gt, cls_pred, t)
            t_aps.append(ap)
        if t_aps:
            coco_aps.append(sum(t_aps) / len(t_aps))
    mAP = sum(coco_aps) / len(coco_aps) if coco_aps else 0.0

    avg_iou = sum(all_ious) / len(all_ious) if all_ious else 0.0

    return LayoutMetricsReport(
        mAP=round(mAP, 4),
        mAP_50=round(mAP_50, 4),
        mAP_75=round(mAP_75, 4),
        avg_iou=round(avg_iou, 4),
        per_class_ap=per_class_ap,
        per_class_count=per_class_count,
        total_gt=len(all_gt),
        total_pred=len(all_pred),
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
    )
