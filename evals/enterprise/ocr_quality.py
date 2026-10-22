"""OCR quality metrics — WER (Word Error Rate) and CER (Character Error Rate).

These measure raw OCR accuracy before any post-processing or extraction.
Lower is better: WER=0 means perfect, WER=1 means every word is wrong.
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict


class OCRQualityReport(TypedDict, total=False):
    wer: Required[float]
    cer: Required[float]
    word_count_gt: int
    word_count_pred: int
    char_count_gt: int
    char_count_pred: int
    insertions: int
    deletions: int
    substitutions: int
    normalized_edit_distance: float
    per_page: list[dict[str, float]]
    metadata: dict[str, Any]


def _tokenize_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\S+", text)]


def _edit_distance_ops(ref: list, hyp: list) -> tuple[int, int, int]:
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    ops = [[(0, 0, 0)] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
        ops[i][0] = (0, i, 0)
    for j in range(m + 1):
        dp[0][j] = j
        ops[0][j] = (j, 0, 0)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                ops[i][j] = ops[i - 1][j - 1]
            else:
                sub = dp[i - 1][j - 1] + 1
                ins = dp[i][j - 1] + 1
                dele = dp[i - 1][j] + 1
                best = min(sub, ins, dele)
                dp[i][j] = best

                s, d, ins_c = ops[i - 1][j - 1]
                if best == sub:
                    ops[i][j] = (ins_c, d, s + 1)
                elif best == dele:
                    s2, d2, ins2 = ops[i - 1][j]
                    ops[i][j] = (ins2, d2 + 1, s2)
                else:
                    s3, d3, ins3 = ops[i][j - 1]
                    ops[i][j] = (ins3 + 1, d3, s3)

    total_ops = dp[n][m]
    insertions = 0
    deletions = 0
    substitutions = 0

    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            substitutions += 1
            i -= 1
            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            insertions += 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            deletions += 1
            i -= 1
        else:
            break

    return insertions, deletions, substitutions


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = _tokenize_words(reference)
    hyp_words = _tokenize_words(hypothesis)
    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    prev = list(range(len(hyp_words) + 1))
    for i in range(1, len(ref_words) + 1):
        curr = [i]
        for j in range(1, len(hyp_words) + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr

    return round(prev[-1] / len(ref_words), 4)


def compute_cer(reference: str, hypothesis: str) -> float:
    ref_chars = list(reference.lower().strip())
    hyp_chars = list(hypothesis.lower().strip())
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    prev = list(range(len(hyp_chars) + 1))
    for i in range(1, len(ref_chars) + 1):
        curr = [i]
        for j in range(1, len(hyp_chars) + 1):
            cost = 0 if ref_chars[i - 1] == hyp_chars[j - 1] else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr

    return round(prev[-1] / len(ref_chars), 4)


def evaluate_ocr_quality(
    references: list[str],
    hypotheses: list[str],
) -> OCRQualityReport:
    if len(references) != len(hypotheses):
        raise ValueError("references and hypotheses must have same length")

    wers: list[float] = []
    cers: list[float] = []
    per_page: list[dict[str, float]] = []
    total_ref_words = 0
    total_pred_words = 0
    total_ref_chars = 0
    total_pred_chars = 0

    for ref, hyp in zip(references, hypotheses):
        w = compute_wer(ref, hyp)
        c = compute_cer(ref, hyp)
        wers.append(w)
        cers.append(c)
        ref_w = len(_tokenize_words(ref))
        hyp_w = len(_tokenize_words(hyp))
        total_ref_words += ref_w
        total_pred_words += hyp_w
        total_ref_chars += len(ref)
        total_pred_chars += len(hyp)
        per_page.append({"wer": w, "cer": c, "ref_words": float(ref_w), "hyp_words": float(hyp_w)})

    avg_wer = sum(wers) / len(wers) if wers else 0.0
    avg_cer = sum(cers) / len(cers) if cers else 0.0

    return OCRQualityReport(
        wer=round(avg_wer, 4),
        cer=round(avg_cer, 4),
        word_count_gt=total_ref_words,
        word_count_pred=total_pred_words,
        char_count_gt=total_ref_chars,
        char_count_pred=total_pred_chars,
        per_page=per_page,
    )
