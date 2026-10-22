from __future__ import annotations
from typing_extensions import Required, TypedDict
import re


class LanguageDetection(TypedDict, total=False):
    language: Required[str]
    confidence: Required[float]
    script: str


TRIGRAM_PROFILES: dict[str, set[str]] = {
    "en": {"the", "and", "ing", "tion", "ent", "her", "for", "tha", "nth", "ion",
           "ted", "ere", "hat", "all", "ith", "ter", "was", "ous", "not", "his",
           "ate", "rea", "com", "est", "men", "ver", "con", "are", "pro", "thi"},
    "de": {"ein", "ich", "und", "der", "die", "den", "sch", "ung", "gen", "cht",
           "ver", "ber", "eit", "ner", "ter", "ine", "auf", "ent", "hen", "uch"},
    "fr": {"les", "des", "ent", "que", "ion", "ons", "ait", "ant", "par", "our",
           "est", "eur", "tion", "ment", "com", "pas", "pou", "sur", "aux", "tre"},
    "es": {"que", "ción", "los", "las", "ent", "ment", "por", "para", "con", "est",
           "ado", "ion", "del", "una", "son", "como", "más", "pero", "todo", "ser"},
    "it": {"che", "zione", "del", "per", "con", "non", "una", "sono", "gli", "dal",
           "ment", "ato", "ità", "lla", "all", "ion", "nte", "ell", "ere", "ono"},
    "pt": {"que", "ção", "dos", "para", "com", "uma", "não", "por", "são", "ment",
           "ado", "est", "nte", "mais", "como", "seu", "mos", "ter", "ica", "ria"},
    "nl": {"een", "het", "van", "den", "ver", "der", "aan", "oor", "ijk", "sch",
           "ing", "aar", "ten", "gen", "ond", "erd", "cht", "ste", "ren", "end"},
    "ja": set(),  # Detected by script
    "zh": set(),  # Detected by script
    "ko": set(),  # Detected by script
    "ar": set(),  # Detected by script
    "hi": set(),  # Detected by script
}

SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "cjk": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF)],
    "hiragana": [(0x3040, 0x309F)],
    "katakana": [(0x30A0, 0x30FF)],
    "hangul": [(0xAC00, 0xD7AF), (0x1100, 0x11FF)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF)],
    "devanagari": [(0x0900, 0x097F)],
    "cyrillic": [(0x0400, 0x04FF), (0x0500, 0x052F)],
    "latin": [(0x0041, 0x024F)],
}


def _detect_script(text: str) -> dict[str, float]:
    counts: dict[str, int] = {}
    total = 0
    for c in text:
        cp = ord(c)
        if cp < 0x20:
            continue
        total += 1
        for script, ranges in SCRIPT_RANGES.items():
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    counts[script] = counts.get(script, 0) + 1
                    break

    if total == 0:
        return {}
    return {s: round(c / total, 4) for s, c in counts.items()}


def _trigram_score(text: str, profile: set[str]) -> float:
    if not profile:
        return 0.0
    text_lower = re.sub(r"[^a-z ]", "", text.lower())
    words = text_lower.split()
    trigrams: set[str] = set()
    for w in words:
        for i in range(len(w) - 2):
            trigrams.add(w[i:i + 3])
    if not trigrams:
        return 0.0
    overlap = len(trigrams & profile)
    return round(overlap / len(profile), 4)


def detect_languages(text: str, top_n: int = 3) -> list[LanguageDetection]:
    if not text or len(text.strip()) < 10:
        return [LanguageDetection(language="en", confidence=0.5, script="latin")]

    scripts = _detect_script(text)

    results: list[LanguageDetection] = []

    cjk = scripts.get("cjk", 0)
    hira = scripts.get("hiragana", 0)
    kata = scripts.get("katakana", 0)
    hangul = scripts.get("hangul", 0)
    arabic = scripts.get("arabic", 0)
    devanagari = scripts.get("devanagari", 0)
    cyrillic = scripts.get("cyrillic", 0)

    if hira + kata > 0.1:
        results.append(LanguageDetection(language="ja", confidence=round(min(hira + kata + cjk, 1.0), 4), script="japanese"))
    if hangul > 0.1:
        results.append(LanguageDetection(language="ko", confidence=round(hangul, 4), script="hangul"))
    if cjk > 0.3 and hira + kata < 0.05 and hangul < 0.05:
        results.append(LanguageDetection(language="zh", confidence=round(cjk, 4), script="cjk"))
    if arabic > 0.2:
        results.append(LanguageDetection(language="ar", confidence=round(arabic, 4), script="arabic"))
    if devanagari > 0.2:
        results.append(LanguageDetection(language="hi", confidence=round(devanagari, 4), script="devanagari"))
    if cyrillic > 0.3:
        results.append(LanguageDetection(language="ru", confidence=round(cyrillic, 4), script="cyrillic"))

    latin = scripts.get("latin", 0)
    if latin > 0.3 or not results:
        scored: list[tuple[str, float]] = []
        for lang, profile in TRIGRAM_PROFILES.items():
            if not profile:
                continue
            score = _trigram_score(text, profile)
            if score > 0.05:
                scored.append((lang, score))

        scored.sort(key=lambda x: -x[1])
        for lang, score in scored[:3]:
            conf = round(min(score * 2.0, 0.95), 4)
            results.append(LanguageDetection(language=lang, confidence=conf, script="latin"))

    if not results:
        results.append(LanguageDetection(language="en", confidence=0.5, script="latin"))

    results.sort(key=lambda x: -x["confidence"])
    return results[:top_n]
