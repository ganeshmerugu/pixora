from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.evals.matchers import token_f1, normalize_text


class DedupPair(TypedDict, total=False):
    doc_a: Required[str]
    doc_b: Required[str]
    similarity: Required[float]
    is_duplicate: Required[bool]
    expected_duplicate: bool
    matching_fields: list[str]


class DedupEvalResult(TypedDict, total=False):
    total_pairs: Required[int]
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: Required[float]
    recall: Required[float]
    f1: Required[float]
    threshold_used: float
    pairs: list[DedupPair]
    metadata: dict[str, Any]


REQUIRED_FIELD_WEIGHT = 2.0
OPTIONAL_FIELD_WEIGHT = 1.0

KEY_FIELDS: dict[str, list[str]] = {
    "invoice": ["invoice_number", "vendor_name", "total_due", "invoice_date"],
    "receipt": ["receipt_number", "merchant_name", "total", "date"],
    "contract": ["contract_number", "party_a", "party_b", "effective_date"],
    "medical": ["mrn", "patient_name", "collection_date"],
    "bank_statement": ["account_number", "statement_date", "ending_balance"],
    "insurance": ["policy_number", "insured_name", "effective_date"],
}


def document_similarity(
    doc_a: dict,
    doc_b: dict,
    doc_type: str = "",
) -> tuple[float, list[str]]:
    expected_a = doc_a.get("expected", doc_a)
    expected_b = doc_b.get("expected", doc_b)

    shared_fields = set(expected_a.keys()) & set(expected_b.keys())
    shared_fields = {f for f in shared_fields if not f.startswith("__")}

    if not shared_fields:
        return 0.0, []

    key_fields = set(KEY_FIELDS.get(doc_type, []))
    weighted_sum = 0.0
    total_weight = 0.0
    matching_fields: list[str] = []

    for field in shared_fields:
        val_a = str(expected_a.get(field, "")).strip()
        val_b = str(expected_b.get(field, "")).strip()
        if not val_a or not val_b:
            continue

        weight = REQUIRED_FIELD_WEIGHT if field in key_fields else OPTIONAL_FIELD_WEIGHT
        sim = token_f1(val_a, val_b)
        weighted_sum += sim * weight
        total_weight += weight

        if sim >= 0.85:
            matching_fields.append(field)

    if total_weight == 0:
        return 0.0, []
    return round(weighted_sum / total_weight, 4), matching_fields


def evaluate_dedup(
    documents: list[dict],
    expected_duplicate_pairs: list[tuple[str, str]],
    threshold: float = 0.90,
) -> DedupEvalResult:
    expected_set: set[tuple[str, str]] = set()
    for a, b in expected_duplicate_pairs:
        expected_set.add((min(a, b), max(a, b)))

    doc_map: dict[str, dict] = {}
    for doc in documents:
        doc_id = doc.get("document_id", "")
        if doc_id:
            doc_map[doc_id] = doc

    pairs: list[DedupPair] = []
    doc_ids = sorted(doc_map.keys())
    tp = fp = fn = tn = 0

    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            id_a, id_b = doc_ids[i], doc_ids[j]
            pair_key = (min(id_a, id_b), max(id_a, id_b))

            doc_type = doc_map[id_a].get("doc_type", "")
            sim, matching_fields = document_similarity(
                doc_map[id_a], doc_map[id_b], doc_type,
            )

            is_dup = sim >= threshold
            expected_dup = pair_key in expected_set

            if is_dup and expected_dup:
                tp += 1
            elif is_dup and not expected_dup:
                fp += 1
            elif not is_dup and expected_dup:
                fn += 1
            else:
                tn += 1

            pairs.append(DedupPair(
                doc_a=id_a, doc_b=id_b,
                similarity=sim, is_duplicate=is_dup,
                expected_duplicate=expected_dup,
                matching_fields=matching_fields,
            ))

    precision = round(tp / max(tp + fp, 1), 4)
    recall = round(tp / max(tp + fn, 1), 4)
    f1 = (
        round(2 * precision * recall / (precision + recall), 4)
        if (precision + recall) > 0 else 0.0
    )

    return DedupEvalResult(
        total_pairs=len(pairs),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=precision,
        recall=recall,
        f1=f1,
        threshold_used=threshold,
        pairs=pairs,
    )
