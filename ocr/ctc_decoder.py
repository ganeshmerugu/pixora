"""CTC decoding — greedy, prefix beam search with N-gram LM, and forward-backward.

Implements the decoding stage of the OCR pipeline:
  Y ∈ ℝ^(T×|L'|)  →  l* = argmax( log P_CTC + α·log P_LM + β·len )

Works with any engine that exposes frame-wise log-probabilities.
"""
from __future__ import annotations
import json
import math
import re
from collections import defaultdict
from typing import Any

import numpy as np


BLANK_IDX = 0

DEFAULT_ALPHABET = (
    " !\"#$%&'()*+,-./0123456789:;<=>?@"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
    "abcdefghijklmnopqrstuvwxyz{|}~"
)


def build_label_map(alphabet: str = DEFAULT_ALPHABET) -> dict[int, str]:
    return {0: "<blank>"} | {i + 1: c for i, c in enumerate(alphabet)}


def build_index_map(alphabet: str = DEFAULT_ALPHABET) -> dict[str, int]:
    return {"<blank>": 0} | {c: i + 1 for i, c in enumerate(alphabet)}


# ── Greedy Decoder ───────────────────────────────────────────────


def greedy_decode(log_probs: np.ndarray, alphabet: str = DEFAULT_ALPHABET) -> str:
    """Argmax per frame → collapse blanks and repeats.

    Args:
        log_probs: (T, |L'|) log-probability matrix.
        alphabet: character set (index 0 reserved for blank).
    """
    label_map = build_label_map(alphabet)
    best_path = np.argmax(log_probs, axis=1)

    collapsed: list[str] = []
    prev = -1
    for idx in best_path:
        idx = int(idx)
        if idx != prev:
            if idx != BLANK_IDX:
                collapsed.append(label_map.get(idx, ""))
        prev = idx

    return "".join(collapsed)


# ── N-Gram Language Model ────────────────────────────────────────


class NGramLM:
    """Character-level or word-level N-gram language model with Laplace smoothing."""

    def __init__(self, n: int = 3, level: str = "char", smoothing: float = 1.0):
        self.n = n
        self.level = level
        self.smoothing = smoothing
        self._counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._totals: dict[str, int] = defaultdict(int)
        self._vocab_size = 0

    def train(self, corpus: str) -> None:
        tokens = list(corpus) if self.level == "char" else corpus.split()
        vocab: set[str] = set()

        for i in range(len(tokens) - self.n + 1):
            context = tuple(tokens[i : i + self.n - 1])
            target = tokens[i + self.n - 1]
            ctx_key = " ".join(context)
            self._counts[ctx_key][target] += 1
            self._totals[ctx_key] += 1
            vocab.add(target)

        self._vocab_size = len(vocab)

    def log_prob(self, context: str, token: str) -> float:
        tokens = list(context) if self.level == "char" else context.split()
        ctx = tokens[-(self.n - 1) :] if len(tokens) >= self.n - 1 else tokens
        ctx_key = " ".join(ctx)

        count = self._counts.get(ctx_key, {}).get(token, 0)
        total = self._totals.get(ctx_key, 0)
        vocab = max(self._vocab_size, 1)

        return math.log((count + self.smoothing) / (total + self.smoothing * vocab))

    def score_sequence(self, text: str) -> float:
        tokens = list(text) if self.level == "char" else text.split()
        if len(tokens) < self.n:
            return 0.0

        total = 0.0
        for i in range(self.n - 1, len(tokens)):
            context = " ".join(tokens[max(0, i - self.n + 1) : i])
            total += self.log_prob(context, tokens[i])
        return total

    def save(self, path: str) -> None:
        data = {
            "n": self.n,
            "level": self.level,
            "smoothing": self.smoothing,
            "counts": {k: dict(v) for k, v in self._counts.items()},
            "totals": dict(self._totals),
            "vocab_size": self._vocab_size,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> NGramLM:
        with open(path) as f:
            data = json.load(f)
        lm = cls(n=data["n"], level=data["level"], smoothing=data["smoothing"])
        lm._counts = defaultdict(lambda: defaultdict(int))
        for k, v in data["counts"].items():
            for tok, cnt in v.items():
                lm._counts[k][tok] = cnt
        lm._totals = defaultdict(int, data["totals"])
        lm._vocab_size = data["vocab_size"]
        return lm


# ── Prefix Beam Search Decoder ───────────────────────────────────


class BeamSearchDecoder:
    """CTC prefix beam search with optional N-gram LM rescoring.

    score = log P_CTC(l|Y) + α·log P_LM(l) + β·|l|
    """

    def __init__(
        self,
        alphabet: str = DEFAULT_ALPHABET,
        beam_width: int = 10,
        lm: NGramLM | None = None,
        lm_weight: float = 0.3,
        length_bonus: float = 0.1,
    ):
        self.alphabet = alphabet
        self.beam_width = beam_width
        self.lm = lm
        self.lm_weight = lm_weight
        self.length_bonus = length_bonus
        self.label_map = build_label_map(alphabet)
        self.vocab_size = len(alphabet) + 1

    def decode(self, log_probs: np.ndarray) -> str:
        T, V = log_probs.shape
        assert V == self.vocab_size, f"Expected vocab size {self.vocab_size}, got {V}"

        # beam: prefix → (p_blank, p_non_blank)
        beam: dict[str, tuple[float, float]] = {"": (0.0, float("-inf"))}

        for t in range(T):
            new_beam: dict[str, tuple[float, float]] = defaultdict(
                lambda: (float("-inf"), float("-inf"))
            )

            for prefix, (p_b, p_nb) in sorted(
                beam.items(), key=lambda x: _logsumexp(x[1][0], x[1][1]), reverse=True
            )[: self.beam_width]:
                p_total = _logsumexp(p_b, p_nb)

                # blank extension
                old_b, old_nb = new_beam[prefix]
                new_beam[prefix] = (
                    _logsumexp(old_b, p_total + log_probs[t, BLANK_IDX]),
                    old_nb,
                )

                for c_idx in range(1, V):
                    c = self.label_map[c_idx]
                    lp = log_probs[t, c_idx]

                    if prefix and c == prefix[-1]:
                        # same char: only extend from blank
                        new_prefix = prefix + c
                        old_b2, old_nb2 = new_beam[new_prefix]
                        new_beam[new_prefix] = (old_b2, _logsumexp(old_nb2, p_b + lp))

                        # also allow staying (from non-blank → repeat collapsed)
                        old_b3, old_nb3 = new_beam[prefix]
                        new_beam[prefix] = (old_b3, _logsumexp(old_nb3, p_nb + lp))
                    else:
                        new_prefix = prefix + c
                        old_b2, old_nb2 = new_beam[new_prefix]
                        new_beam[new_prefix] = (
                            old_b2,
                            _logsumexp(old_nb2, p_total + lp),
                        )

            beam = dict(new_beam)

        # Final scoring with LM and length bonus
        best_prefix = ""
        best_score = float("-inf")
        for prefix, (p_b, p_nb) in beam.items():
            score = _logsumexp(p_b, p_nb)
            if self.lm and prefix:
                score += self.lm_weight * self.lm.score_sequence(prefix)
            score += self.length_bonus * len(prefix)
            if score > best_score:
                best_score = score
                best_prefix = prefix

        return best_prefix


# ── Forward-Backward Algorithm ───────────────────────────────────


def ctc_forward(log_probs: np.ndarray, label_sequence: list[int]) -> np.ndarray:
    """Compute CTC forward variables α_t(s).

    Args:
        log_probs: (T, V) log-probability matrix.
        label_sequence: target label indices (without blanks).

    Returns:
        alpha: (T, |l'|) forward log-probabilities where l' is the
               blank-interleaved label sequence.
    """
    T, V = log_probs.shape

    # Interleave blanks: l' = (ε, l1, ε, l2, ..., ε, l_N, ε)
    L = len(label_sequence)
    Lp = 2 * L + 1
    labels_prime = [BLANK_IDX] * Lp
    for i, l in enumerate(label_sequence):
        labels_prime[2 * i + 1] = l

    alpha = np.full((T, Lp), float("-inf"), dtype=np.float64)

    # Init
    alpha[0, 0] = log_probs[0, BLANK_IDX]
    if Lp > 1:
        alpha[0, 1] = log_probs[0, labels_prime[1]]

    for t in range(1, T):
        for s in range(Lp):
            lp_s = labels_prime[s]
            # Case 1: same state
            a = alpha[t - 1, s]
            # Case 2: previous state
            if s > 0:
                a = _logsumexp(a, alpha[t - 1, s - 1])
            # Case 3: skip blank between different labels
            if s > 1 and lp_s != BLANK_IDX and lp_s != labels_prime[s - 2]:
                a = _logsumexp(a, alpha[t - 1, s - 2])

            alpha[t, s] = a + log_probs[t, lp_s]

    return alpha


def ctc_backward(log_probs: np.ndarray, label_sequence: list[int]) -> np.ndarray:
    """Compute CTC backward variables β_t(s)."""
    T, V = log_probs.shape
    L = len(label_sequence)
    Lp = 2 * L + 1
    labels_prime = [BLANK_IDX] * Lp
    for i, l in enumerate(label_sequence):
        labels_prime[2 * i + 1] = l

    beta = np.full((T, Lp), float("-inf"), dtype=np.float64)

    beta[T - 1, Lp - 1] = 0.0
    if Lp > 1:
        beta[T - 1, Lp - 2] = 0.0

    for t in range(T - 2, -1, -1):
        for s in range(Lp):
            lp_s = labels_prime[s]
            b = beta[t + 1, s] + log_probs[t + 1, lp_s]
            if s < Lp - 1:
                b = _logsumexp(b, beta[t + 1, s + 1] + log_probs[t + 1, labels_prime[s + 1]])
            if s < Lp - 2 and labels_prime[s + 2] != BLANK_IDX and labels_prime[s + 2] != lp_s:
                b = _logsumexp(b, beta[t + 1, s + 2] + log_probs[t + 1, labels_prime[s + 2]])

            beta[t, s] = b

    return beta


def ctc_log_probability(log_probs: np.ndarray, label_sequence: list[int]) -> float:
    """Compute log P(l|Y) using the forward algorithm."""
    alpha = ctc_forward(log_probs, label_sequence)
    T = alpha.shape[0]
    Lp = alpha.shape[1]
    return _logsumexp(alpha[T - 1, Lp - 1], alpha[T - 1, Lp - 2]) if Lp > 1 else alpha[T - 1, 0]


def ctc_loss(log_probs: np.ndarray, label_sequence: list[int]) -> float:
    """CTC loss = -log P(l|Y)."""
    return -ctc_log_probability(log_probs, label_sequence)


# ── Utilities ────────────────────────────────────────────────────


def _logsumexp(a: float, b: float) -> float:
    if a == float("-inf"):
        return b
    if b == float("-inf"):
        return a
    mx = max(a, b)
    return mx + math.log(math.exp(a - mx) + math.exp(b - mx))
