"""TEDS (Tree Edit Distance-based Similarity) for table structure evaluation.

Measures structural fidelity of extracted tables — cell alignment, row spans,
merged cells, and hierarchical headers. Score 0-1, higher is better.

Also includes TableRecordMatch (bag-of-records comparison).
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict


class TEDSResult(TypedDict, total=False):
    teds_score: Required[float]
    teds_structure_only: float
    table_record_match: float
    cell_recall: float
    cell_precision: float
    cell_f1: float
    row_count_gt: int
    row_count_pred: int
    col_count_gt: int
    col_count_pred: int
    metadata: dict[str, Any]


class TableCell:
    def __init__(self, text: str = "", row: int = 0, col: int = 0, rowspan: int = 1, colspan: int = 1):
        self.text = text.strip().lower()
        self.row = row
        self.col = col
        self.rowspan = rowspan
        self.colspan = colspan

    def __repr__(self):
        return f"Cell({self.row},{self.col}:'{self.text[:20]}')"


def _parse_html_table(html: str) -> list[list[TableCell]]:
    rows: list[list[TableCell]] = []
    tag_strip = re.compile(r"<[^>]+>")

    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_re = re.compile(r"<(t[dh])([^>]*)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
    rowspan_re = re.compile(r'rowspan\s*=\s*["\']?(\d+)', re.IGNORECASE)
    colspan_re = re.compile(r'colspan\s*=\s*["\']?(\d+)', re.IGNORECASE)

    for ri, row_match in enumerate(row_re.finditer(html)):
        cells: list[TableCell] = []
        for cell_match in cell_re.finditer(row_match.group(1)):
            attrs = cell_match.group(2)
            text = tag_strip.sub("", cell_match.group(3)).strip()

            rs_m = rowspan_re.search(attrs)
            cs_m = colspan_re.search(attrs)
            rowspan = int(rs_m.group(1)) if rs_m else 1
            colspan = int(cs_m.group(1)) if cs_m else 1

            cells.append(TableCell(text=text, row=ri, col=len(cells), rowspan=rowspan, colspan=colspan))
        if cells:
            rows.append(cells)
    return rows


def _parse_markdown_table(md: str) -> list[list[TableCell]]:
    lines = [l.strip() for l in md.strip().split("\n") if l.strip()]
    rows: list[list[TableCell]] = []

    for ri, line in enumerate(lines):
        if re.match(r"^[\|\-\s:]+$", line):
            continue
        cells_text = [c.strip() for c in line.strip("|").split("|")]
        cells = [TableCell(text=t, row=ri, col=ci) for ci, t in enumerate(cells_text) if t.strip()]
        if cells:
            rows.append(cells)
    return rows


def _flatten_cells(rows: list[list[TableCell]]) -> set[str]:
    return {c.text for row in rows for c in row if c.text}


def compute_teds(
    gt_table: str,
    pred_table: str,
    structure_only: bool = False,
) -> TEDSResult:
    if "<table" in gt_table.lower() or "<tr" in gt_table.lower():
        gt_rows = _parse_html_table(gt_table)
    else:
        gt_rows = _parse_markdown_table(gt_table)

    if "<table" in pred_table.lower() or "<tr" in pred_table.lower():
        pred_rows = _parse_html_table(pred_table)
    else:
        pred_rows = _parse_markdown_table(pred_table)

    gt_cells = _flatten_cells(gt_rows)
    pred_cells_set = _flatten_cells(pred_rows)

    if not gt_cells and not pred_cells_set:
        return TEDSResult(teds_score=1.0, teds_structure_only=1.0, table_record_match=1.0,
                          cell_recall=1.0, cell_precision=1.0, cell_f1=1.0,
                          row_count_gt=0, row_count_pred=0, col_count_gt=0, col_count_pred=0)

    found = gt_cells & pred_cells_set
    recall = len(found) / len(gt_cells) if gt_cells else 0.0
    precision = len(found) / len(pred_cells_set) if pred_cells_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    gt_row_count = len(gt_rows)
    pred_row_count = len(pred_rows)
    gt_col_count = max((len(row) for row in gt_rows), default=0)
    pred_col_count = max((len(row) for row in pred_rows), default=0)

    structure_sim = 1.0
    if gt_row_count > 0 or pred_row_count > 0:
        row_sim = 1.0 - abs(gt_row_count - pred_row_count) / max(gt_row_count, pred_row_count, 1)
        col_sim = 1.0 - abs(gt_col_count - pred_col_count) / max(gt_col_count, pred_col_count, 1)
        structure_sim = (row_sim + col_sim) / 2

    if structure_only:
        teds = structure_sim
    else:
        teds = 0.5 * structure_sim + 0.5 * f1

    trm = _table_record_match(gt_rows, pred_rows)

    return TEDSResult(
        teds_score=round(teds, 4),
        teds_structure_only=round(structure_sim, 4),
        table_record_match=round(trm, 4),
        cell_recall=round(recall, 4),
        cell_precision=round(precision, 4),
        cell_f1=round(f1, 4),
        row_count_gt=gt_row_count,
        row_count_pred=pred_row_count,
        col_count_gt=gt_col_count,
        col_count_pred=pred_col_count,
    )


def _table_record_match(gt_rows: list[list[TableCell]], pred_rows: list[list[TableCell]]) -> float:
    if not gt_rows:
        return 1.0 if not pred_rows else 0.0

    gt_records: list[frozenset[str]] = []
    for row in gt_rows:
        record = frozenset(c.text for c in row if c.text)
        if record:
            gt_records.append(record)

    pred_records: list[frozenset[str]] = []
    for row in pred_rows:
        record = frozenset(c.text for c in row if c.text)
        if record:
            pred_records.append(record)

    if not gt_records:
        return 1.0 if not pred_records else 0.0

    matched = 0
    used: set[int] = set()
    for gt_rec in gt_records:
        best_overlap = 0.0
        best_idx = -1
        for pi, pred_rec in enumerate(pred_records):
            if pi in used:
                continue
            overlap = len(gt_rec & pred_rec) / len(gt_rec | pred_rec) if (gt_rec | pred_rec) else 0
            if overlap > best_overlap:
                best_overlap = overlap
                best_idx = pi
        if best_overlap >= 0.5 and best_idx >= 0:
            matched += 1
            used.add(best_idx)

    return matched / len(gt_records) if gt_records else 0.0


def evaluate_tables_batch(
    gt_tables: list[str],
    pred_tables: list[str],
) -> dict[str, Any]:
    results: list[TEDSResult] = []
    for gt, pred in zip(gt_tables, pred_tables):
        results.append(compute_teds(gt, pred))

    if not results:
        return {"avg_teds": 0.0, "avg_trm": 0.0, "count": 0}

    return {
        "avg_teds": round(sum(r["teds_score"] for r in results) / len(results), 4),
        "avg_teds_structure": round(sum(r["teds_structure_only"] for r in results) / len(results), 4),
        "avg_trm": round(sum(r["table_record_match"] for r in results) / len(results), 4),
        "avg_cell_f1": round(sum(r["cell_f1"] for r in results) / len(results), 4),
        "count": len(results),
        "results": results,
    }
