from __future__ import annotations
import os
import re
from pixora.models.pipeline import DocumentProfile

import functools

@functools.lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


KEYWORD_RULES: list[dict] = [
    {
        "doc_type": "invoice",
        "patterns": [r"\binvoice\b", r"\binv[.\-#]\s*\d", r"\bbill\s*to\b", r"\btotal\s*due\b", r"\bamount\s*due\b"],
        "min_matches": 2,
        "weight": 10,
    },
    {
        "doc_type": "receipt",
        "patterns": [r"\breceipt\b", r"\bsubtotal\b", r"\bchange\s*due\b", r"\bcashier\b", r"\bstore\s*#?\d", r"\btotal\b.*\$", r"\bpayment\b"],
        "min_matches": 2,
        "weight": 10,
    },
    {
        "doc_type": "contract",
        "patterns": [
            r"\bagreement\b", r"\bterms\s*(and|&)\s*conditions\b", r"\bparties\b", r"\bhereby\b",
            r"\bgoverning\s*law\b", r"\btermination\b", r"\bindemnif", r"\bclause\b",
            r"\beffective\s*date\b", r"\bexpiration\s*date\b",
        ],
        "min_matches": 2,
        "weight": 12,
    },
    {
        "doc_type": "medical",
        "patterns": [
            r"\bpatient\s*name\b", r"\bmrn\b", r"\bdiagnosis\b", r"\bicd[.\-\s]*10\b",
            r"\bmedication\b", r"\bprescri", r"\bvitals?\b", r"\bblood\s*pressure\b",
            r"\bhba1c\b", r"\blab\s*results?\b", r"\battending\s*physician\b",
            r"\bmedical\s*report\b", r"\bhospital\b", r"\bclinic\b",
        ],
        "min_matches": 3,
        "weight": 15,
    },
    {
        "doc_type": "insurance",
        "patterns": [
            r"\bclaim\s*(number|#|no)\b", r"\bpolicy\s*(number|#|no)\b", r"\bpolicyholder\b",
            r"\bdeductible\b", r"\bpremium\b", r"\bcoverage\b", r"\binsurance\s*claim\b",
            r"\bestimated\s*repair\b", r"\bamount\s*requested\b", r"\bclaimant\b",
        ],
        "min_matches": 2,
        "weight": 14,
    },
    {
        "doc_type": "scientific_paper",
        "patterns": [r"\babstract\b", r"\bintroduction\b", r"\breferences\b", r"\bmethodology\b", r"\bconclusion\b"],
        "min_matches": 3,
        "weight": 10,
    },
    {
        "doc_type": "form",
        "patterns": [
            r"\bapplication\s*for\b", r"\bsection\s*\d", r"\[\s*\]", r"\bplease\s*(fill|complete)\b",
            r"\bapplicant\b", r"\bposition\s*applied\b", r"\bemployment\s*history\b",
        ],
        "min_matches": 2,
        "weight": 11,
    },
    {
        "doc_type": "id_card",
        "patterns": [
            r"\bpermanent\s*account\s*number\b", r"\baadhaar\b", r"\buidai\b",
            r"\bincome\s*tax\s*department\b", r"\bgovt\s*of\s*india\b", r"\bgovernment\s*of\s*india\b",
            r"\bpassport\s*no\b", r"\bdriving\s*licen[cs]e\b",
            r"\bvoter\s*id\b", r"\belection\s*commission\b",
        ],
        "min_matches": 2,
        "weight": 8,
    },
    {
        "doc_type": "bank_statement",
        "patterns": [
            r"\baccount\s*statement\b", r"\bopening\s*balance\b", r"\bclosing\s*balance\b",
            r"\bdebit\b.*\bcredit\b", r"\btransaction\s*date\b", r"\bbank\s*statement\b",
        ],
        "min_matches": 2,
        "weight": 12,
    },
    {
        "doc_type": "shipping",
        "patterns": [
            r"\btracking\s*(number|#|no)\b", r"\bshipper\b", r"\bconsignee\b",
            r"\bwaybill\b", r"\bfreight\b", r"\bcarrier\b", r"\bbill\s*of\s*lading\b",
        ],
        "min_matches": 2,
        "weight": 12,
    },
]

EXTENSION_MAP: dict[str, str] = {
    ".pdf": "document",
    ".docx": "document", ".doc": "document",
    ".xlsx": "spreadsheet", ".xls": "spreadsheet", ".csv": "spreadsheet",
    ".html": "webpage", ".htm": "webpage",
    ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".tiff": "image", ".tif": "image", ".bmp": "image",
    ".webp": "image", ".heic": "image", ".heif": "image", ".avif": "image",
    ".svg": "image", ".gif": "image", ".ico": "image",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".heic", ".heif", ".avif", ".svg", ".gif", ".ico"}


class RuleBasedClassifier:
    def classify_by_rules(self, filename: str, first_page_text: str) -> DocumentProfile:
        ext = os.path.splitext(filename)[1].lower()
        is_scanned = ext in IMAGE_EXTENSIONS
        text_lower = first_page_text.lower()

        best_type = EXTENSION_MAP.get(ext, "document")
        best_confidence = 0.3
        best_score = 0

        for rule in KEYWORD_RULES:
            matches = sum(1 for p in rule["patterns"] if _compile_pattern(p).search(text_lower))
            if matches >= rule["min_matches"]:
                weight = rule.get("weight", 10)
                score = matches * weight
                if score > best_score:
                    best_type = rule["doc_type"]
                    best_confidence = min(0.5 + (matches * 0.1), 0.85)
                    best_score = score

        has_tables = bool(
            re.search(r"\|.*\|.*\|", first_page_text)
            or re.search(r"\t.*\t.*\t", first_page_text)
            or re.search(r"^\s*\w+\s{2,}\w+\s{2,}\w+", first_page_text, re.MULTILINE)
        )

        has_handwriting = self._detect_handwriting_hints(first_page_text)
        text_layer_present = bool(first_page_text.strip()) and not is_scanned
        complexity = self._compute_complexity(first_page_text, has_tables, has_handwriting, is_scanned)

        return DocumentProfile(
            doc_type=best_type,
            confidence=best_confidence,
            complexity=complexity,
            is_scanned=is_scanned,
            text_layer_present=text_layer_present,
            has_tables=has_tables,
            has_handwriting=has_handwriting,
            has_images=is_scanned,
            metadata={"classifier_stage": "rules", "keyword_score": best_score},
        )

    def _detect_handwriting_hints(self, text: str) -> bool:
        handwriting_markers = [
            r"\bhandwrit", r"\bhand\s*written\b", r"\bmanuscript\b",
            r"\[handwritten\]", r"\bsignature\b", r"\bsigned\s*by\b",
            r"\binitials?\b", r"\bcursive\b",
        ]
        text_lower = text.lower()
        matches = sum(1 for p in handwriting_markers if re.search(p, text_lower))
        return matches >= 1

    def _compute_complexity(
        self, text: str, has_tables: bool, has_handwriting: bool, is_scanned: bool,
    ) -> float:
        score = 0.0
        words = text.split()
        word_count = len(words)

        if word_count > 2000:
            score += 0.2
        elif word_count > 500:
            score += 0.1

        if has_tables:
            score += 0.15

        if has_handwriting:
            score += 0.2

        if is_scanned:
            score += 0.1

        unique_words = set(w.lower() for w in words if w.isalpha())
        if word_count > 0 and unique_words:
            diversity = len(unique_words) / word_count
            if diversity > 0.7:
                score += 0.1

        from pixora.ocr.language_detector import detect_languages
        if text.strip():
            langs = detect_languages(text[:2000])
            if len(langs) > 1 and langs[1]["confidence"] > 0.2:
                score += 0.15

        return round(min(score, 1.0), 2)
