from __future__ import annotations
import re
import logging
from typing import Any
from typing_extensions import Required, TypedDict
from Levenshtein import distance as lev_distance
from pixora.ocr.engine import RecognizedRegion, RecognizedWord
from pixora.ocr.json_utils import extract_json_object
from pixora.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class CorrectionRecord(TypedDict, total=False):
    word_index: int
    original: Required[str]
    corrected: Required[str]
    reason: Required[str]
    confidence_delta: float


class HITLFlag(TypedDict, total=False):
    field: str
    region_id: str
    word_index: int
    word_text: str
    confidence: float
    reason: str
    suggested_corrections: list[str]


class PostProcessedRegion(TypedDict, total=False):
    region_id: Required[str]
    original_text: str
    corrected_text: Required[str]
    corrections: list[CorrectionRecord]
    final_confidence: float
    hitl_flags: list[HITLFlag]
    llm_validated: bool


# --- OCR Confusion Pairs (65+ bidirectional) ---

COMMON_OCR_CONFUSIONS: dict[str, str] = {
    # Letter-digit confusions
    "rn": "m", "vv": "w", "cl": "d", "li": "h", "ii": "u",
    "nn": "m", "ri": "n", "lll": "ill", "ln": "in",
    # Zero/O confusions
    "O": "0", "o": "0",
    # One/l/I confusions
    "l": "1", "I": "1",
    # S/5 confusions
    "S": "5", "s": "5",
    # B/8 confusions
    "B": "8",
    # Z/2 confusions
    "Z": "2", "z": "2",
    # G/6 confusions
    "G": "6",
    # g/9 confusions
    "g": "9", "q": "9",
    # D/O confusions
    "D": "0",
    # Punctuation confusions
    ".": ",",
    ";": ":",
    "!": "1",
    "/": "I",
    "\\": "I",
    # Common OCR multi-char errors
    "tl": "d", "fi": "fi", "fl": "fl",
    "iii": "m", "iil": "ill",
}

REVERSE_CONFUSIONS: dict[str, str] = {
    # Digit-to-letter (when in word context)
    "0": "O", "1": "l", "5": "S", "8": "B", "2": "Z", "6": "G", "9": "g",
    "I": "/",
}

UNICODE_LOOKALIKES: dict[str, str] = {
    "а": "a",  # Cyrillic а → Latin a
    "е": "e",  # Cyrillic е → Latin e
    "о": "o",  # Cyrillic о → Latin o
    "р": "p",  # Cyrillic р → Latin p
    "с": "c",  # Cyrillic с → Latin c
    "у": "y",  # Cyrillic у → Latin y
    "х": "x",  # Cyrillic х → Latin x
    "А": "A",  # Cyrillic А → Latin A
    "В": "B",  # Cyrillic В → Latin B
    "Е": "E",  # Cyrillic Е → Latin E
    "К": "K",  # Cyrillic К → Latin K
    "М": "M",  # Cyrillic М → Latin M
    "Н": "H",  # Cyrillic Н → Latin H
    "О": "O",  # Cyrillic О → Latin O
    "Р": "P",  # Cyrillic Р → Latin P
    "С": "C",  # Cyrillic С → Latin C
    "Т": "T",  # Cyrillic Т → Latin T
    "Х": "X",  # Cyrillic Х → Latin X
    "‘": "'",  # Left single quote
    "’": "'",  # Right single quote
    "“": '"',  # Left double quote
    "”": '"',  # Right double quote
    "–": "-",  # En dash
    "—": "-",  # Em dash
    " ": " ",  # Non-breaking space
}

# --- Domain Dictionaries (200+ terms per domain) ---

FINANCIAL_TERMS: frozenset[str] = frozenset({
    "invoice", "receipt", "total", "subtotal", "tax", "discount", "amount",
    "balance", "payment", "credit", "debit", "account", "vendor", "customer",
    "quantity", "price", "unit", "description", "date", "due", "paid", "net",
    "gross", "vat", "shipping", "handling", "fee", "charge", "refund",
    "purchase", "order", "billing", "address", "remittance", "wire", "transfer",
    "routing", "currency", "exchange", "rate", "terms", "conditions",
    "payable", "receivable", "ledger", "journal", "statement", "reconciliation",
    "deposit", "withdrawal", "transaction", "reference", "number", "memo",
    "approved", "pending", "overdue", "installment", "interest", "principal",
    "maturity", "accrual", "depreciation", "amortization", "revenue", "expense",
    "profit", "loss", "margin", "budget", "forecast", "variance", "audit",
    "compliance", "fiscal", "quarter", "annual", "monthly", "weekly",
    "check", "cheque", "draft", "promissory", "note", "bond", "equity",
    "dividend", "yield", "portfolio", "asset", "liability", "capital",
    "cost", "adjustment", "allocation", "reimbursement", "advance", "prepaid",
    "accrued", "deferred", "retained", "earnings", "stockholder", "shareholder",
    "consolidated", "subsidiary", "affiliate", "entity", "corporation",
    "partnership", "proprietorship", "limited", "incorporated", "registered",
    "exemption", "withholding", "deduction", "taxable", "exempt", "bracket",
    "filing", "return", "assessment", "penalty", "surcharge", "levy",
    "customs", "duty", "tariff", "import", "export", "clearance",
    "consignment", "inventory", "warehouse", "logistics", "procurement",
    "supplier", "manufacturer", "distributor", "retailer", "wholesale",
    "catalog", "quotation", "estimate", "proposal", "acceptance", "rejection",
    "confirmation", "acknowledgment", "delivery", "shipment", "tracking",
    "carrier", "freight", "postage", "handling", "insurance", "coverage",
    "premium", "policy", "claim", "beneficiary", "underwriter",
})

LEGAL_TERMS: frozenset[str] = frozenset({
    "agreement", "contract", "party", "parties", "herein", "hereto", "hereby",
    "whereas", "therefore", "witness", "signature", "notary", "effective",
    "termination", "liability", "indemnify", "jurisdiction", "amendment",
    "clause", "provision", "obligation", "breach", "remedy", "governing",
    "arbitration", "mediation", "dispute", "resolution", "settlement",
    "confidentiality", "nondisclosure", "noncompete", "intellectual", "property",
    "patent", "trademark", "copyright", "license", "royalty", "exclusive",
    "nonexclusive", "assignable", "transferable", "irrevocable", "perpetual",
    "severability", "waiver", "estoppel", "force", "majeure", "consequential",
    "incidental", "punitive", "damages", "injunctive", "relief", "equitable",
    "statutory", "regulatory", "compliance", "representation", "warranty",
    "covenant", "recital", "preamble", "schedule", "exhibit", "appendix",
    "addendum", "supplement", "modification", "renewal", "extension",
    "consideration", "capacity", "authority", "binding", "enforceable",
    "executed", "counterpart", "original", "duplicate", "certified",
    "notarized", "authenticated", "legalized", "apostille", "sworn",
    "affidavit", "declaration", "deposition", "testimony", "evidence",
    "plaintiff", "defendant", "appellant", "respondent", "petitioner",
    "counsel", "attorney", "solicitor", "barrister", "advocate",
    "tribunal", "court", "magistrate", "judge", "jury", "verdict",
    "judgment", "decree", "order", "injunction", "subpoena", "summons",
    "complaint", "motion", "brief", "memorandum", "opinion", "ruling",
    "precedent", "statute", "regulation", "ordinance", "bylaw",
    "fiduciary", "trustee", "beneficiary", "executor", "administrator",
    "guardian", "conservator", "custodian", "proxy", "power",
})

MEDICAL_TERMS: frozenset[str] = frozenset({
    "patient", "diagnosis", "prescription", "medication", "dosage", "physician",
    "hospital", "treatment", "symptoms", "allergies", "insurance", "provider",
    "referral", "laboratory", "results", "blood", "pressure", "weight",
    "temperature", "pulse", "respiratory", "oxygen", "saturation",
    "hemoglobin", "hematocrit", "platelet", "leukocyte", "erythrocyte",
    "glucose", "cholesterol", "triglyceride", "creatinine", "albumin",
    "bilirubin", "alkaline", "phosphatase", "transaminase", "electrolyte",
    "sodium", "potassium", "calcium", "magnesium", "chloride", "bicarbonate",
    "urinalysis", "culture", "sensitivity", "pathology", "biopsy",
    "radiology", "imaging", "ultrasound", "mammogram", "colonoscopy",
    "endoscopy", "echocardiogram", "electrocardiogram", "spirometry",
    "anesthesia", "surgery", "procedure", "operation", "transplant",
    "rehabilitation", "therapy", "physical", "occupational", "speech",
    "psychiatric", "psychology", "counseling", "behavioral", "cognitive",
    "cardiology", "neurology", "oncology", "orthopedic", "dermatology",
    "gastroenterology", "pulmonology", "endocrinology", "nephrology",
    "urology", "obstetrics", "gynecology", "pediatrics", "geriatrics",
    "emergency", "intensive", "critical", "ambulatory", "outpatient",
    "inpatient", "discharge", "admission", "transfer", "consultation",
    "prognosis", "chronic", "acute", "benign", "malignant", "metastatic",
    "remission", "relapse", "complication", "adverse", "contraindication",
    "immunization", "vaccination", "prophylaxis", "screening", "preventive",
    "palliative", "hospice", "triage", "stabilization", "resuscitation",
    "intubation", "ventilation", "dialysis", "transfusion", "infusion",
    "specimen", "collection", "phlebotomy", "centrifuge", "microscopy",
    "clinical", "attending", "resident", "intern", "nurse", "technician",
})

GOVERNMENT_TERMS: frozenset[str] = frozenset({
    "certificate", "registration", "license", "permit", "identification",
    "passport", "visa", "citizenship", "residency", "immigration",
    "birth", "death", "marriage", "divorce", "adoption",
    "social", "security", "number", "taxpayer", "employer",
    "department", "ministry", "bureau", "agency", "commission",
    "federal", "state", "county", "municipal", "district",
    "election", "voter", "ballot", "candidate", "constituency",
    "legislation", "regulation", "ordinance", "statute", "code",
    "enforcement", "inspection", "compliance", "violation", "penalty",
    "revenue", "treasury", "customs", "immigration", "naturalization",
    "veteran", "military", "defense", "intelligence", "homeland",
})

DOMAIN_DICTIONARIES: dict[str, frozenset[str]] = {
    "invoice": FINANCIAL_TERMS,
    "receipt": FINANCIAL_TERMS,
    "contract": LEGAL_TERMS,
    "medical": MEDICAL_TERMS,
    "bank_statement": FINANCIAL_TERMS,
    "insurance": FINANCIAL_TERMS | LEGAL_TERMS,
    "government": GOVERNMENT_TERMS,
    "shipping": FINANCIAL_TERMS,
    "form": FINANCIAL_TERMS | GOVERNMENT_TERMS,
    "default": FINANCIAL_TERMS | LEGAL_TERMS | MEDICAL_TERMS,
}

_DATE_PATTERN = re.compile(r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b")
_AMOUNT_PATTERN = re.compile(r"^\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?$")
_ID_PATTERN = re.compile(r"^[A-Z]{2,4}[-#]?\d{3,}$")
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_PATTERN = re.compile(r"^[\+]?[(]?\d{1,4}[)]?[-\s\./0-9]{7,15}$")
_NEAR_AMOUNT_PATTERN = re.compile(r"^\$?[\dOolI,]+\.[\dOolI]{2}$")

VISUAL_CONFUSION_COSTS: dict[tuple[str, str], float] = {}

def _build_confusion_costs() -> dict[tuple[str, str], float]:
    costs: dict[tuple[str, str], float] = {}
    for wrong, right in COMMON_OCR_CONFUSIONS.items():
        if len(wrong) == 1 and len(right) == 1:
            costs[(wrong, right)] = 0.3
            costs[(right, wrong)] = 0.3
    for wrong, right in REVERSE_CONFUSIONS.items():
        if len(wrong) == 1 and len(right) == 1:
            costs[(wrong, right)] = 0.3
            costs[(right, wrong)] = 0.3
    for orig, norm in UNICODE_LOOKALIKES.items():
        if len(orig) == 1 and len(norm) == 1:
            costs[(orig, norm)] = 0.1
            costs[(norm, orig)] = 0.1
    return costs

VISUAL_CONFUSION_COSTS = _build_confusion_costs()


def weighted_levenshtein(
    a: str,
    b: str,
    sub_costs: dict[tuple[str, str], float] | None = None,
    default_sub: float = 1.0,
    insert_cost: float = 1.0,
    delete_cost: float = 1.0,
) -> float:
    costs = sub_costs or VISUAL_CONFUSION_COSTS
    m, n = len(a), len(b)
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i * delete_cost
    for j in range(n + 1):
        dp[0][j] = j * insert_cost

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                sc = costs.get((a[i - 1], b[j - 1]), default_sub)
                dp[i][j] = min(
                    dp[i - 1][j] + delete_cost,
                    dp[i][j - 1] + insert_cost,
                    dp[i - 1][j - 1] + sc,
                )
    return dp[m][n]


HITL_CONFIDENCE_THRESHOLD = 0.70

LLM_VALIDATION_PROMPT = """You are a document quality checker. Review this extracted text for errors.

Document type: {doc_type}
Extracted text:
{text}

Check for:
1. Words that look like OCR misreads (e.g., "rn" should be "m", "0" vs "O")
2. Numbers that don't make sense in context (e.g., totals that don't add up)
3. Dates that are malformed or impossible
4. Names/addresses that appear corrupted

Return JSON:
{{
  "corrections": [
    {{"original": "word", "corrected": "word", "reason": "explanation"}}
  ],
  "confidence": 0.95,
  "issues": ["description of any semantic issues found"]
}}

If no corrections needed, return {{"corrections": [], "confidence": 0.98, "issues": []}}"""


class OCRPostProcessor:
    def __init__(
        self,
        custom_dictionary: set[str] | None = None,
        llm: LLMProvider | None = None,
        hitl_threshold: float = HITL_CONFIDENCE_THRESHOLD,
    ):
        self.custom_dictionary = frozenset(custom_dictionary) if custom_dictionary else frozenset()
        self.llm = llm
        self.hitl_threshold = hitl_threshold
        self._lev_cache: dict[tuple[str, str], int] = {}

    async def process_async(
        self,
        regions: list[RecognizedRegion],
        doc_type: str = "",
        schema_hints: dict[str, str] | None = None,
    ) -> list[PostProcessedRegion]:
        results = self.process(regions, doc_type, schema_hints)

        if self.llm:
            for result in results:
                text = result["corrected_text"]
                if len(text) > 10:
                    validated = await self._llm_validate(text, doc_type)
                    result["llm_validated"] = True
                    for correction in validated.get("corrections", []):
                        orig = correction.get("original", "")
                        fixed = correction.get("corrected", "")
                        if orig and fixed and orig != fixed and orig in result["corrected_text"]:
                            result["corrected_text"] = result["corrected_text"].replace(orig, fixed)
                            result["corrections"].append(CorrectionRecord(
                                original=orig, corrected=fixed,
                                reason=f"llm_validation: {correction.get('reason', '')}",
                                confidence_delta=0.05,
                            ))

        return results

    def process(
        self,
        regions: list[RecognizedRegion],
        doc_type: str = "",
        schema_hints: dict[str, str] | None = None,
    ) -> list[PostProcessedRegion]:
        domain_dict = self._get_domain_dictionary(doc_type)
        hint_patterns = self._compile_schema_hints(schema_hints) if schema_hints else {}
        results: list[PostProcessedRegion] = []

        for region in regions:
            corrections: list[CorrectionRecord] = []
            hitl_flags: list[HITLFlag] = []
            words = region.get("words", [])
            corrected_parts: list[str] = []

            if not words:
                hitl = self._check_region_hitl(region)
                text = self._fix_unicode_lookalikes(region["text"])
                results.append(PostProcessedRegion(
                    region_id=region["region_id"],
                    original_text=region["text"],
                    corrected_text=text,
                    corrections=[],
                    final_confidence=region["confidence"],
                    hitl_flags=hitl,
                    llm_validated=False,
                ))
                continue

            for i, word in enumerate(words):
                text = word["text"]
                conf = word["confidence"]
                corrected = self._fix_unicode_lookalikes(text)

                if corrected != text:
                    corrections.append(CorrectionRecord(
                        word_index=i, original=text, corrected=corrected,
                        reason="unicode_normalization", confidence_delta=0.05,
                    ))

                new_corrected, c = self._confusion_fix(corrected, domain_dict)
                if c:
                    corrections.append(CorrectionRecord(
                        word_index=i, original=corrected, corrected=new_corrected,
                        reason="confusion_pair", confidence_delta=0.15,
                    ))
                    corrected = new_corrected

                if conf < 0.8:
                    dict_match = self._dictionary_correct(corrected, domain_dict)
                    if dict_match and dict_match != corrected.lower():
                        corrections.append(CorrectionRecord(
                            word_index=i, original=corrected, corrected=dict_match,
                            reason="dictionary_match", confidence_delta=0.1,
                        ))
                        corrected = dict_match

                if conf < 0.6:
                    pattern_fix = self._pattern_correct(corrected, doc_type)
                    if pattern_fix != corrected:
                        corrections.append(CorrectionRecord(
                            word_index=i, original=corrected, corrected=pattern_fix,
                            reason="pattern_match", confidence_delta=0.1,
                        ))
                        corrected = pattern_fix

                if hint_patterns:
                    hint_fix = self._apply_schema_hints(corrected, hint_patterns)
                    if hint_fix != corrected:
                        corrections.append(CorrectionRecord(
                            word_index=i, original=corrected, corrected=hint_fix,
                            reason="schema_hint", confidence_delta=0.08,
                        ))
                        corrected = hint_fix

                if conf < self.hitl_threshold:
                    suggestions = self._suggest_alternatives(corrected, domain_dict)
                    hitl_flags.append(HITLFlag(
                        region_id=region["region_id"],
                        word_index=i,
                        word_text=corrected,
                        confidence=conf,
                        reason="low_confidence" if conf < 0.5 else "below_threshold",
                        suggested_corrections=suggestions,
                    ))

                corrected_parts.append(corrected)

            corrected_text = " ".join(corrected_parts)

            correction_boost = min(len(corrections) * 0.03, 0.15)
            hitl_penalty = len(hitl_flags) * 0.02
            final_conf = min(1.0, region["confidence"] + correction_boost - hitl_penalty)

            results.append(PostProcessedRegion(
                region_id=region["region_id"],
                original_text=region["text"],
                corrected_text=corrected_text,
                corrections=corrections,
                final_confidence=max(0.0, final_conf),
                hitl_flags=hitl_flags,
                llm_validated=False,
            ))

        return results

    def _fix_unicode_lookalikes(self, text: str) -> str:
        result = []
        for c in text:
            result.append(UNICODE_LOOKALIKES.get(c, c))
        return "".join(result)

    def _get_domain_dictionary(self, doc_type: str) -> frozenset[str]:
        base = DOMAIN_DICTIONARIES.get(doc_type, DOMAIN_DICTIONARIES["default"])
        if self.custom_dictionary:
            return base | self.custom_dictionary
        return base

    def _confusion_fix(self, text: str, domain_dict: frozenset[str]) -> tuple[str, bool]:
        changed = False
        text_lower = text.lower()
        for wrong, right in COMMON_OCR_CONFUSIONS.items():
            if wrong in text_lower:
                candidate = text_lower.replace(wrong, right)
                if candidate in domain_dict:
                    text = candidate
                    changed = True
                    break
        if not changed:
            for wrong, right in REVERSE_CONFUSIONS.items():
                if wrong in text and text.isalpha() is False:
                    candidate = text.replace(wrong, right)
                    if candidate.lower() in domain_dict:
                        text = candidate
                        changed = True
                        break
        return text, changed

    def _cached_lev(self, a: str, b: str) -> float:
        key = (a, b) if a <= b else (b, a)
        if key not in self._lev_cache:
            self._lev_cache[key] = weighted_levenshtein(a, b)
        return self._lev_cache[key]

    def _dictionary_correct(self, word: str, domain_dict: frozenset[str]) -> str | None:
        lower = word.lower()
        if lower in domain_dict:
            return None

        best_match = None
        best_dist = 2.5
        for term in domain_dict:
            if abs(len(term) - len(lower)) > 2:
                continue
            if len(term) <= 3:
                continue
            dist = self._cached_lev(lower, term)
            if dist < best_dist:
                best_dist = dist
                best_match = term

        return best_match

    def _pattern_correct(self, text: str, doc_type: str) -> str:
        if _AMOUNT_PATTERN.match(text):
            return text.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
        if _DATE_PATTERN.match(text):
            return text.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
        if _ID_PATTERN.match(text):
            num_part = re.sub(r"[A-Z\-#]", "", text)
            fixed = num_part.replace("O", "0").replace("o", "0").replace("l", "1")
            return text[:len(text) - len(num_part)] + fixed

        if _NEAR_AMOUNT_PATTERN.match(text):
            fixed = text.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
            if fixed != text:
                return fixed

        return text

    def _compile_schema_hints(self, hints: dict[str, str]) -> dict[str, re.Pattern]:
        compiled: dict[str, re.Pattern] = {}
        for field, pattern_str in hints.items():
            try:
                compiled[field] = re.compile(pattern_str)
            except re.error:
                logger.warning("postprocessor: invalid regex hint for field '%s': %s", field, pattern_str)
        return compiled

    def _apply_schema_hints(self, text: str, hint_patterns: dict[str, re.Pattern]) -> str:
        for field, pattern in hint_patterns.items():
            m = pattern.search(text)
            if m:
                return m.group(0)
        return text

    def _suggest_alternatives(self, word: str, domain_dict: frozenset[str]) -> list[str]:
        lower = word.lower()
        scored: list[tuple[str, float]] = []
        for term in domain_dict:
            if abs(len(term) - len(lower)) > 2:
                continue
            if len(term) <= 2:
                continue
            dist = self._cached_lev(lower, term)
            if 0 < dist <= 2.5:
                scored.append((term, dist))

        scored.sort(key=lambda x: x[1])
        return [t for t, _ in scored[:3]]

    def _check_region_hitl(self, region: RecognizedRegion) -> list[HITLFlag]:
        if region["confidence"] < self.hitl_threshold:
            return [HITLFlag(
                region_id=region["region_id"],
                confidence=region["confidence"],
                reason="low_region_confidence",
            )]
        return []

    async def _llm_validate(self, text: str, doc_type: str) -> dict:
        prompt = LLM_VALIDATION_PROMPT.format(doc_type=doc_type or "general", text=text[:3000])
        try:
            resp = await self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            content = resp["content"]
            return extract_json_object(content) or {"corrections": [], "confidence": 0.5, "issues": []}
        except Exception as exc:
            logger.warning("postprocessor: LLM validation failed: %s", exc)
            return {"corrections": [], "confidence": 0.5, "issues": []}
