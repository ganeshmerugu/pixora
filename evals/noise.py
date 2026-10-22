from __future__ import annotations
import random
import string
from typing import Any
from typing_extensions import TypedDict


class NoiseConfig(TypedDict, total=False):
    char_error_rate: float
    word_drop_rate: float
    swap_rate: float
    case_flip_rate: float
    ocr_confusion_map: bool


DEFAULT_NOISE_CONFIG: NoiseConfig = {
    "char_error_rate": 0.02,
    "word_drop_rate": 0.01,
    "swap_rate": 0.01,
    "case_flip_rate": 0.005,
    "ocr_confusion_map": True,
}

NOISE_LEVELS: dict[str, NoiseConfig] = {
    "light": {
        "char_error_rate": 0.01,
        "word_drop_rate": 0.005,
        "swap_rate": 0.005,
        "case_flip_rate": 0.002,
        "ocr_confusion_map": True,
    },
    "moderate": {
        "char_error_rate": 0.03,
        "word_drop_rate": 0.02,
        "swap_rate": 0.015,
        "case_flip_rate": 0.01,
        "ocr_confusion_map": True,
    },
    "heavy": {
        "char_error_rate": 0.06,
        "word_drop_rate": 0.04,
        "swap_rate": 0.03,
        "case_flip_rate": 0.02,
        "ocr_confusion_map": True,
    },
    "adversarial": {
        "char_error_rate": 0.10,
        "word_drop_rate": 0.06,
        "swap_rate": 0.05,
        "case_flip_rate": 0.03,
        "ocr_confusion_map": True,
    },
}

OCR_CONFUSIONS: dict[str, list[str]] = {
    "0": ["O", "o", "Q"],
    "O": ["0", "o", "Q"],
    "o": ["0", "O"],
    "1": ["l", "I", "|", "i"],
    "l": ["1", "I", "|", "i"],
    "I": ["1", "l", "|"],
    "i": ["1", "l", "!"],
    "5": ["S", "s"],
    "S": ["5", "s"],
    "s": ["5", "S"],
    "8": ["B", "3"],
    "B": ["8", "3"],
    "2": ["Z", "z"],
    "Z": ["2", "z"],
    "6": ["G", "b"],
    "G": ["6", "C"],
    "9": ["g", "q"],
    "g": ["9", "q"],
    "m": ["rn", "nn"],
    "rn": ["m"],
    "w": ["vv"],
    "D": ["O", "0"],
    "C": ["G", "("],
    "n": ["ri", "h"],
    "h": ["b", "n"],
    "t": ["f", "+"],
    "f": ["t"],
    ".": [","],
    ",": ["."],
    ";": [":"],
    ":": [";"],
}


def inject_ocr_noise(
    text: str,
    config: NoiseConfig | None = None,
    seed: int | None = None,
) -> str:
    cfg = config or DEFAULT_NOISE_CONFIG
    rng = random.Random(seed)

    chars = list(text)
    use_confusions = cfg.get("ocr_confusion_map", True)
    char_err = cfg.get("char_error_rate", 0.02)
    swap = cfg.get("swap_rate", 0.01)
    case_flip = cfg.get("case_flip_rate", 0.005)

    if use_confusions:
        i = 0
        while i < len(chars):
            c = chars[i]
            if c in OCR_CONFUSIONS and rng.random() < char_err:
                replacement = rng.choice(OCR_CONFUSIONS[c])
                chars[i:i + 1] = list(replacement)
                i += len(replacement)
            else:
                i += 1

    for i in range(len(chars)):
        if chars[i].isalnum() and rng.random() < char_err:
            if chars[i].isdigit():
                chars[i] = rng.choice(string.digits)
            elif chars[i].isupper():
                chars[i] = rng.choice(string.ascii_uppercase)
            else:
                chars[i] = rng.choice(string.ascii_lowercase)

    for i in range(len(chars) - 1):
        if rng.random() < swap and chars[i].isalnum() and chars[i + 1].isalnum():
            chars[i], chars[i + 1] = chars[i + 1], chars[i]

    for i in range(len(chars)):
        if chars[i].isalpha() and rng.random() < case_flip:
            chars[i] = chars[i].swapcase()

    result = "".join(chars)

    word_drop = cfg.get("word_drop_rate", 0.01)
    if word_drop > 0:
        words = result.split(" ")
        kept = [w for w in words if rng.random() >= word_drop or not w.strip()]
        result = " ".join(kept)

    return result


def generate_noisy_benchmarks(
    clean_benchmarks: list[dict],
    noise_levels: list[str] | None = None,
) -> list[dict]:
    levels = noise_levels or ["light", "moderate", "heavy"]
    noisy: list[dict] = []
    for bench in clean_benchmarks:
        for level_name in levels:
            cfg = NOISE_LEVELS.get(level_name, DEFAULT_NOISE_CONFIG)
            doc_id = bench.get("document_id", "unknown")
            text = bench.get("text", "")
            seed = hash(f"{doc_id}_{level_name}") & 0xFFFFFFFF
            noisy_text = inject_ocr_noise(text, cfg, seed=seed)
            noisy_bench = {**bench}
            noisy_bench["document_id"] = f"{doc_id}_noise_{level_name}"
            noisy_bench["text"] = noisy_text
            noisy_bench["noise_level"] = level_name
            noisy_bench["noise_seed"] = seed
            noisy.append(noisy_bench)
    return noisy
