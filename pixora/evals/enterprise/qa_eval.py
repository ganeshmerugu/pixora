"""Downstream QA evaluation — tests whether parsed output is usable by an LLM.

Simulates DocVQA/ChartQA/InfographicVQA by asking questions about parsed content
and checking if the answer can be found. This is the ultimate test: if the LLM
can't find the answer in your parsed output, your parser broke something.
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.matchers import composite_match, token_f1


class QAPair(TypedDict, total=False):
    question: Required[str]
    answer: Required[str]
    doc_id: str
    category: str
    difficulty: str


class QAResult(TypedDict, total=False):
    question: Required[str]
    expected_answer: Required[str]
    found: Required[bool]
    match_score: float
    best_span: str
    method: str


class QAEvalReport(TypedDict, total=False):
    accuracy: Required[float]
    anls_score: Required[float]
    exact_match_rate: float
    fuzzy_match_rate: float
    total_questions: int
    answered: int
    by_category: dict[str, dict[str, float]]
    by_difficulty: dict[str, dict[str, float]]
    results: list[QAResult]
    metadata: dict[str, Any]


def _normalize_answer(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\.\,\-\$\%]", "", text)
    return text


def _find_answer_in_text(answer: str, parsed_text: str, threshold: float = 0.7) -> tuple[bool, float, str, str]:
    norm_answer = _normalize_answer(answer)
    norm_text = _normalize_answer(parsed_text)

    if norm_answer in norm_text:
        return True, 1.0, answer, "exact_substring"

    words = norm_text.split()
    answer_len = len(norm_answer.split())
    best_score = 0.0
    best_span = ""

    window = max(answer_len, 1)
    for size in range(max(1, window - 2), min(window + 5, len(words) + 1)):
        for i in range(len(words) - size + 1):
            span = " ".join(words[i:i + size])
            result = composite_match(span, norm_answer)
            score = result["score"]
            if score > best_score:
                best_score = score
                best_span = span

    if best_score >= threshold:
        return True, best_score, best_span, "fuzzy_match"

    tf1 = token_f1(norm_text, norm_answer)
    if tf1 >= threshold:
        return True, tf1, "", "token_overlap"

    return False, best_score, best_span, "not_found"


def _compute_anls(score: float, threshold: float = 0.5) -> float:
    return score if score >= threshold else 0.0


def evaluate_qa(
    parsed_text: str,
    qa_pairs: list[QAPair],
    threshold: float = 0.7,
) -> QAEvalReport:
    results: list[QAResult] = []
    answered = 0
    anls_scores: list[float] = []
    exact = 0
    fuzzy = 0

    cat_scores: dict[str, list[float]] = {}
    diff_scores: dict[str, list[float]] = {}

    for qa in qa_pairs:
        found, score, span, method = _find_answer_in_text(qa["answer"], parsed_text, threshold)

        if found:
            answered += 1
        if method == "exact_substring":
            exact += 1
        if method in ("exact_substring", "fuzzy_match"):
            fuzzy += 1

        anls = _compute_anls(score)
        anls_scores.append(anls)

        cat = qa.get("category", "general")
        cat_scores.setdefault(cat, []).append(anls)
        diff = qa.get("difficulty", "medium")
        diff_scores.setdefault(diff, []).append(anls)

        results.append(QAResult(
            question=qa["question"],
            expected_answer=qa["answer"],
            found=found,
            match_score=round(score, 4),
            best_span=span[:100],
            method=method,
        ))

    n = len(qa_pairs)
    accuracy = answered / n if n else 0.0
    avg_anls = sum(anls_scores) / n if n else 0.0

    by_cat: dict[str, dict[str, float]] = {}
    for cat, scores in cat_scores.items():
        by_cat[cat] = {
            "anls": round(sum(scores) / len(scores), 4),
            "accuracy": round(sum(1 for s in scores if s > 0) / len(scores), 4),
            "count": float(len(scores)),
        }

    by_diff: dict[str, dict[str, float]] = {}
    for diff, scores in diff_scores.items():
        by_diff[diff] = {
            "anls": round(sum(scores) / len(scores), 4),
            "accuracy": round(sum(1 for s in scores if s > 0) / len(scores), 4),
            "count": float(len(scores)),
        }

    return QAEvalReport(
        accuracy=round(accuracy, 4),
        anls_score=round(avg_anls, 4),
        exact_match_rate=round(exact / n, 4) if n else 0.0,
        fuzzy_match_rate=round(fuzzy / n, 4) if n else 0.0,
        total_questions=n,
        answered=answered,
        by_category=by_cat,
        by_difficulty=by_diff,
        results=results,
    )


INVOICE_QA_PAIRS: list[QAPair] = [
    QAPair(question="What is the invoice number?", answer="INV-2024-00891", category="field_extraction"),
    QAPair(question="Who is the vendor?", answer="Acme Corporation", category="field_extraction"),
    QAPair(question="What is the total amount due?", answer="$49,674.22", category="field_extraction"),
    QAPair(question="What are the payment terms?", answer="Net 30", category="field_extraction"),
    QAPair(question="What is the due date?", answer="04/14/2024", category="field_extraction"),
    QAPair(question="What is the bill-to company name?", answer="TechStart Inc.", category="field_extraction"),
    QAPair(question="What is the tax amount?", answer="$4,049.22", category="field_extraction"),
    QAPair(question="How much is the Cloud Infrastructure Setup?", answer="$12,500.00", category="line_item"),
    QAPair(question="What is the subtotal?", answer="$45,625.00", category="line_item"),
    QAPair(question="How many API Integration hours were billed?", answer="40", category="line_item", difficulty="hard"),
]

MEDICAL_QA_PAIRS: list[QAPair] = [
    QAPair(question="What is the patient name?", answer="Robert J. Williams", category="field_extraction"),
    QAPair(question="What is the MRN?", answer="MRN-00284719", category="field_extraction"),
    QAPair(question="What is the diagnosis?", answer="Pre-diabetic condition", category="field_extraction"),
    QAPair(question="What is the fasting glucose level?", answer="112", category="lab_value"),
    QAPair(question="What is the hemoglobin level?", answer="14.8", category="lab_value"),
    QAPair(question="Who is the ordering physician?", answer="Dr. Amanda Torres", category="field_extraction"),
    QAPair(question="What is the collection date?", answer="03/08/2024", category="field_extraction"),
    QAPair(question="Is the glucose level flagged as abnormal?", answer="HIGH", category="interpretation", difficulty="hard"),
]
