from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.matchers import composite_match, normalize_text


class LineItemMatch(TypedDict, total=False):
    predicted_index: int
    expected_index: int
    row_similarity: Required[float]
    matched_columns: list[str]
    unmatched_columns: list[str]


class TableEvalMetrics(TypedDict, total=False):
    table_id: str
    row_precision: Required[float]
    row_recall: Required[float]
    row_f1: Required[float]
    column_accuracy: Required[float]
    cell_accuracy: Required[float]
    row_order_score: float
    line_item_matches: list[LineItemMatch]
    unmatched_predicted: list[int]
    unmatched_expected: list[int]
    metadata: dict[str, Any]


def _row_similarity(pred_row: dict, exp_row: dict) -> tuple[float, list[str], list[str]]:
    all_cols = set(pred_row.keys()) | set(exp_row.keys())
    if not all_cols:
        return 1.0, [], []
    matched: list[str] = []
    unmatched: list[str] = []
    total_sim = 0.0

    for col in all_cols:
        p_val = str(pred_row.get(col, ""))
        e_val = str(exp_row.get(col, ""))
        if not p_val and not e_val:
            total_sim += 1.0
            matched.append(col)
            continue
        if not p_val or not e_val:
            unmatched.append(col)
            continue
        result = composite_match(p_val, e_val)
        sim = result["score"]
        total_sim += sim
        if sim >= 0.7:
            matched.append(col)
        else:
            unmatched.append(col)

    return round(total_sim / len(all_cols), 4), matched, unmatched


def _build_similarity_matrix(
    predicted: list[dict],
    expected: list[dict],
) -> list[list[tuple[float, list[str], list[str]]]]:
    matrix: list[list[tuple[float, list[str], list[str]]]] = []
    for p_row in predicted:
        row_sims: list[tuple[float, list[str], list[str]]] = []
        for e_row in expected:
            row_sims.append(_row_similarity(p_row, e_row))
        matrix.append(row_sims)
    return matrix


def _greedy_match(
    matrix: list[list[tuple[float, list[str], list[str]]]],
    threshold: float,
) -> list[tuple[int, int, float, list[str], list[str]]]:
    n_pred = len(matrix)
    n_exp = len(matrix[0]) if matrix else 0

    candidates: list[tuple[float, int, int]] = []
    for i in range(n_pred):
        for j in range(n_exp):
            sim = matrix[i][j][0]
            if sim >= threshold:
                candidates.append((sim, i, j))

    candidates.sort(key=lambda x: -x[0])

    used_pred: set[int] = set()
    used_exp: set[int] = set()
    matches: list[tuple[int, int, float, list[str], list[str]]] = []

    for sim, pi, ei in candidates:
        if pi in used_pred or ei in used_exp:
            continue
        _, matched_cols, unmatched_cols = matrix[pi][ei]
        matches.append((pi, ei, sim, matched_cols, unmatched_cols))
        used_pred.add(pi)
        used_exp.add(ei)

    return matches


def _kendall_tau_normalized(matched_pairs: list[tuple[int, int]]) -> float:
    if len(matched_pairs) < 2:
        return 1.0
    pairs_sorted = sorted(matched_pairs, key=lambda x: x[1])
    pred_order = [p[0] for p in pairs_sorted]
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


def match_line_items(
    predicted_rows: list[dict],
    expected_rows: list[dict],
    match_threshold: float = 0.6,
    table_id: str = "",
) -> TableEvalMetrics:
    if not predicted_rows and not expected_rows:
        return TableEvalMetrics(
            row_precision=1.0, row_recall=1.0, row_f1=1.0,
            column_accuracy=1.0, cell_accuracy=1.0, row_order_score=1.0,
            line_item_matches=[], unmatched_predicted=[], unmatched_expected=[],
            table_id=table_id,
        )
    if not predicted_rows:
        return TableEvalMetrics(
            row_precision=0.0, row_recall=0.0, row_f1=0.0,
            column_accuracy=0.0, cell_accuracy=0.0, row_order_score=0.0,
            line_item_matches=[],
            unmatched_predicted=[],
            unmatched_expected=list(range(len(expected_rows))),
            table_id=table_id,
        )
    if not expected_rows:
        return TableEvalMetrics(
            row_precision=0.0, row_recall=0.0, row_f1=0.0,
            column_accuracy=0.0, cell_accuracy=0.0, row_order_score=0.0,
            line_item_matches=[],
            unmatched_predicted=list(range(len(predicted_rows))),
            unmatched_expected=[],
            table_id=table_id,
        )

    matrix = _build_similarity_matrix(predicted_rows, expected_rows)
    matches = _greedy_match(matrix, match_threshold)

    tp = len(matches)
    row_precision = round(tp / len(predicted_rows), 4) if predicted_rows else 0.0
    row_recall = round(tp / len(expected_rows), 4) if expected_rows else 0.0
    row_f1 = round(
        2 * row_precision * row_recall / (row_precision + row_recall), 4
    ) if (row_precision + row_recall) > 0 else 0.0

    total_cells = 0
    correct_cells = 0
    for pi, ei, sim, matched_cols, unmatched_cols in matches:
        all_cols = set(predicted_rows[pi].keys()) | set(expected_rows[ei].keys())
        total_cells += len(all_cols)
        correct_cells += len(matched_cols)

    cell_accuracy = round(correct_cells / total_cells, 4) if total_cells > 0 else 0.0

    all_pred_cols = set()
    all_exp_cols = set()
    for r in predicted_rows:
        all_pred_cols.update(r.keys())
    for r in expected_rows:
        all_exp_cols.update(r.keys())
    column_accuracy = compute_column_accuracy(sorted(all_pred_cols), sorted(all_exp_cols))

    matched_pairs = [(pi, ei) for pi, ei, *_ in matches]
    row_order = _kendall_tau_normalized(matched_pairs)

    matched_pred = {pi for pi, *_ in matches}
    matched_exp = {ei for _, ei, *_ in matches}

    line_item_matches = [
        LineItemMatch(
            predicted_index=pi, expected_index=ei,
            row_similarity=sim, matched_columns=mcols, unmatched_columns=ucols,
        )
        for pi, ei, sim, mcols, ucols in matches
    ]

    return TableEvalMetrics(
        table_id=table_id,
        row_precision=row_precision,
        row_recall=row_recall,
        row_f1=row_f1,
        column_accuracy=column_accuracy,
        cell_accuracy=cell_accuracy,
        row_order_score=row_order,
        line_item_matches=line_item_matches,
        unmatched_predicted=[i for i in range(len(predicted_rows)) if i not in matched_pred],
        unmatched_expected=[i for i in range(len(expected_rows)) if i not in matched_exp],
    )


def compute_column_accuracy(
    predicted_columns: list[str],
    expected_columns: list[str],
) -> float:
    pred_set = {normalize_text(c) for c in predicted_columns if c}
    exp_set = {normalize_text(c) for c in expected_columns if c}
    if not pred_set and not exp_set:
        return 1.0
    union = pred_set | exp_set
    if not union:
        return 1.0
    return round(len(pred_set & exp_set) / len(union), 4)
