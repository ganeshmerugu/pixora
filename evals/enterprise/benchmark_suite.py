"""Unified enterprise benchmark suite — runs all evaluation dimensions.

Covers:
1. End-to-End parsing (content faithfulness via ParseBench rules)
2. Downstream QA (DocVQA-style answer retrieval)
3. OCR quality (WER/CER)
4. Table structure (TEDS + TableRecordMatch)
5. Layout detection (mAP/IoU)
6. Production metrics (cost/page, latency, throughput, semantic formatting)
"""
from __future__ import annotations
import json
import time
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.evals.enterprise.ocr_quality import evaluate_ocr_quality, OCRQualityReport
from pixora.evals.enterprise.teds import evaluate_tables_batch
from pixora.evals.enterprise.layout_metrics import compute_layout_metrics, LayoutMetricsReport, DetectionBox
from pixora.evals.enterprise.production_metrics import ProductionTracker, ProductionReport, format_production_report
from pixora.evals.enterprise.qa_eval import evaluate_qa, QAEvalReport, QAPair


class EnterpriseBenchmarkReport(TypedDict, total=False):
    pipeline_name: Required[str]
    overall_score: Required[float]

    # 1. End-to-end parsing
    content_faithfulness: float
    text_formatting: float

    # 2. Downstream QA
    qa_accuracy: float
    qa_anls: float
    qa_report: QAEvalReport

    # 3. OCR quality
    wer: float
    cer: float
    ocr_report: OCRQualityReport

    # 4. Table structure
    teds_score: float
    table_record_match: float
    table_report: dict[str, Any]

    # 5. Layout detection
    layout_mAP: float
    layout_avg_iou: float
    layout_report: LayoutMetricsReport

    # 6. Production
    cost_per_page_usd: float
    avg_latency_ms: float
    pages_per_second: float
    semantic_formatting: float
    production_report: ProductionReport

    elapsed_ms: int
    metadata: dict[str, Any]


def run_enterprise_benchmark(
    pipeline_name: str,
    parsed_pages: list[dict[str, Any]],
    gt_pages: list[dict[str, Any]] | None = None,
    qa_pairs: list[QAPair] | None = None,
) -> EnterpriseBenchmarkReport:
    start = time.monotonic()
    report = EnterpriseBenchmarkReport(pipeline_name=pipeline_name, overall_score=0.0)
    dimension_scores: list[float] = []

    # ── 3. OCR Quality (WER/CER) ──────────────────────────────
    if gt_pages:
        refs = [p.get("gt_text", "") for p in gt_pages]
        hyps = [p.get("parsed_text", "") for p in parsed_pages[:len(refs)]]
        refs_filtered = [r for r, h in zip(refs, hyps) if r.strip()]
        hyps_filtered = [h for r, h in zip(refs, hyps) if r.strip()]
        if refs_filtered:
            ocr = evaluate_ocr_quality(refs_filtered, hyps_filtered)
            report["wer"] = ocr["wer"]
            report["cer"] = ocr["cer"]
            report["ocr_report"] = ocr
            ocr_score = 1.0 - min(ocr["wer"], 1.0)
            dimension_scores.append(ocr_score)

    # ── 4. Table Structure (TEDS) ─────────────────────────────
    if gt_pages:
        gt_tables = [p.get("gt_table_html", "") for p in gt_pages if p.get("gt_table_html")]
        pred_tables = [p.get("parsed_table", "") for p in parsed_pages[:len(gt_tables)] if p.get("parsed_table")]
        if gt_tables and pred_tables and len(gt_tables) == len(pred_tables):
            table_result = evaluate_tables_batch(gt_tables, pred_tables)
            report["teds_score"] = table_result["avg_teds"]
            report["table_record_match"] = table_result["avg_trm"]
            report["table_report"] = table_result
            dimension_scores.append(table_result["avg_teds"])

    # ── 5. Layout Detection (mAP/IoU) ─────────────────────────
    if gt_pages:
        gt_box_pages: list[list[DetectionBox]] = []
        pred_box_pages: list[list[DetectionBox]] = []
        for gi, gt_p in enumerate(gt_pages):
            gt_boxes = gt_p.get("gt_boxes", [])
            if gt_boxes and gi < len(parsed_pages):
                gt_box_pages.append(gt_boxes)
                pred_box_pages.append(parsed_pages[gi].get("pred_boxes", []))
        if gt_box_pages:
            layout = compute_layout_metrics(gt_box_pages, pred_box_pages)
            report["layout_mAP"] = layout["mAP"]
            report["layout_avg_iou"] = layout["avg_iou"]
            report["layout_report"] = layout
            dimension_scores.append(layout["mAP"])

    # ── 2. Downstream QA ──────────────────────────────────────
    if qa_pairs:
        all_text = "\n".join(p.get("parsed_text", "") for p in parsed_pages)
        qa_result = evaluate_qa(all_text, qa_pairs)
        report["qa_accuracy"] = qa_result["accuracy"]
        report["qa_anls"] = qa_result["anls_score"]
        report["qa_report"] = qa_result
        dimension_scores.append(qa_result["anls_score"])

    # ── 6. Production Metrics ──────────────────────────────────
    tracker = ProductionTracker()
    tracker.start_batch()
    for p in parsed_pages:
        tracker.record_page(
            cost_usd=p.get("cost_usd", 0.0),
            latency_ms=p.get("latency_ms", 0.0),
            tier=p.get("tier", "tier1"),
            tokens=p.get("tokens", 0),
        )
        for fmt_type in ["bold", "italic", "strikethrough", "superscript", "underline"]:
            if f"gt_{fmt_type}" in p:
                tracker.record_formatting_check(fmt_type, p[f"gt_{fmt_type}"], p.get(f"pred_{fmt_type}", False))

    prod = tracker.get_report()
    report["cost_per_page_usd"] = prod["avg_cost_per_page_usd"]
    report["avg_latency_ms"] = prod["avg_latency_per_page_ms"]
    report["pages_per_second"] = prod.get("pages_per_second", 0)
    report["semantic_formatting"] = prod.get("semantic_formatting_score", 0)
    report["production_report"] = prod

    # ── Overall Score ──────────────────────────────────────────
    if dimension_scores:
        report["overall_score"] = round(sum(dimension_scores) / len(dimension_scores), 4)

    report["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    return report


def format_enterprise_report(report: EnterpriseBenchmarkReport) -> str:
    lines = [
        f"Enterprise Benchmark: {report['pipeline_name']}",
        "=" * 60,
        f"Overall Score: {report['overall_score'] * 100:.1f}%",
        "",
    ]

    sections = [
        ("OCR Quality", [
            ("WER (Word Error Rate)", report.get("wer"), True),
            ("CER (Char Error Rate)", report.get("cer"), True),
        ]),
        ("Table Structure", [
            ("TEDS Score", report.get("teds_score"), False),
            ("Table Record Match", report.get("table_record_match"), False),
        ]),
        ("Layout Detection", [
            ("mAP", report.get("layout_mAP"), False),
            ("Avg IoU", report.get("layout_avg_iou"), False),
        ]),
        ("Downstream QA", [
            ("Accuracy", report.get("qa_accuracy"), False),
            ("ANLS Score", report.get("qa_anls"), False),
        ]),
        ("Production", [
            ("Cost/page", report.get("cost_per_page_usd"), False),
            ("Avg latency", report.get("avg_latency_ms"), False),
            ("Pages/sec", report.get("pages_per_second"), False),
            ("Semantic Formatting", report.get("semantic_formatting"), False),
        ]),
    ]

    for section_name, metrics in sections:
        has_data = any(v is not None for _, v, _ in metrics)
        if not has_data:
            continue
        lines.append(f"\n{section_name}:")
        for name, value, lower_better in metrics:
            if value is not None:
                if isinstance(value, float) and value < 1:
                    display = f"{value * 100:.1f}%" if not name.startswith("Cost") else f"${value:.4f}"
                else:
                    display = f"{value:.1f}ms" if "latency" in name.lower() else f"{value:.2f}"
                indicator = " (lower=better)" if lower_better else ""
                lines.append(f"  {name:<25s} {display}{indicator}")

    return "\n".join(lines)
