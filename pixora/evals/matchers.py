from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
import re


class MatchResult(TypedDict, total=False):
    score: Required[float]
    method: Required[str]
    levenshtein_sim: float
    token_f1: float
    semantic_sim: float
    details: dict[str, Any]


class MatchConfig(TypedDict, total=False):
    levenshtein_weight: float
    token_weight: float
    semantic_weight: float
    normalize: bool


DEFAULT_MATCH_CONFIG: MatchConfig = {
    "levenshtein_weight": 0.4,
    "token_weight": 0.4,
    "semantic_weight": 0.2,
    "normalize": True,
}

_NORMALIZE_RE = re.compile(r"[\s,.$€£¥#\-]+")
_TOKEN_SPLIT_RE = re.compile(r"[\s\-_/,;:.()]+")


def normalize_text(text: str) -> str:
    return _NORMALIZE_RE.sub("", text).lower().strip()


def levenshtein_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def levenshtein_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return round(1.0 - levenshtein_distance(a, b) / max_len, 4)


def token_f1(predicted: str, expected: str) -> float:
    pred_tokens = [t.lower() for t in _TOKEN_SPLIT_RE.split(predicted) if t]
    exp_tokens = [t.lower() for t in _TOKEN_SPLIT_RE.split(expected) if t]
    if not pred_tokens and not exp_tokens:
        return 1.0
    if not pred_tokens or not exp_tokens:
        return 0.0

    pred_bag = {}
    for t in pred_tokens:
        pred_bag[t] = pred_bag.get(t, 0) + 1
    exp_bag = {}
    for t in exp_tokens:
        exp_bag[t] = exp_bag.get(t, 0) + 1

    overlap = 0
    for t, c in pred_bag.items():
        overlap += min(c, exp_bag.get(t, 0))

    precision = overlap / len(pred_tokens) if pred_tokens else 0.0
    recall = overlap / len(exp_tokens) if exp_tokens else 0.0
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def _char_trigrams(text: str) -> set[str]:
    if len(text) < 3:
        return {text} if text else set()
    return {text[i:i + 3] for i in range(len(text) - 2)}


def semantic_similarity(predicted: str, expected: str) -> float:
    p_norm = predicted.lower().strip()
    e_norm = expected.lower().strip()
    if not p_norm and not e_norm:
        return 1.0
    if not p_norm or not e_norm:
        return 0.0
    p_tri = _char_trigrams(p_norm)
    e_tri = _char_trigrams(e_norm)
    intersection = len(p_tri & e_tri)
    union = len(p_tri | e_tri)
    if union == 0:
        return 1.0
    return round(intersection / union, 4)


def composite_match(
    predicted: str,
    expected: str,
    config: MatchConfig | None = None,
) -> MatchResult:
    cfg = config or DEFAULT_MATCH_CONFIG
    do_normalize = cfg.get("normalize", True)
    lev_w = cfg.get("levenshtein_weight", 0.4)
    tok_w = cfg.get("token_weight", 0.4)
    sem_w = cfg.get("semantic_weight", 0.2)

    p = normalize_text(predicted) if do_normalize else predicted
    e = normalize_text(expected) if do_normalize else expected

    lev = levenshtein_similarity(p, e)
    tok = token_f1(predicted, expected)
    sem = semantic_similarity(p, e)

    total_weight = lev_w + tok_w + sem_w
    if total_weight == 0:
        score = 0.0
    else:
        score = round((lev * lev_w + tok * tok_w + sem * sem_w) / total_weight, 4)

    return MatchResult(
        score=score,
        method="composite",
        levenshtein_sim=lev,
        token_f1=tok,
        semantic_sim=sem,
    )
