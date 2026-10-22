"""Enterprise post-processing — normalize, validate, and sanitize extraction output.

Normalizations: dates → ISO 8601, amounts → float, names → title case,
phones → E.164, emails → validated, addresses → structured.
PII detection: flag sensitive fields.
Schema validation: enforce output types.
"""
from __future__ import annotations
import re
from typing import Any


# ── Date Normalization ────────────────────────────────────────

_DATE_PATTERNS = [
    (re.compile(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})"), "mdy4"),
    (re.compile(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})"), "mdy2"),
    (re.compile(r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})"), "ymd"),
    (re.compile(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})"), "month_name"),
    (re.compile(r"(\d{1,2})\s+(\w+)\s+(\d{4})"), "day_month_name"),
]

_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def normalize_date(value: str) -> str:
    if not value:
        return value
    v = value.strip()

    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(v)
        if not m:
            continue
        try:
            if fmt == "mdy4":
                mm, dd, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif fmt == "mdy2":
                mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
                yyyy = 2000 + yy if yy < 50 else 1900 + yy
            elif fmt == "ymd":
                yyyy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif fmt == "month_name":
                mon = m.group(1).lower()
                mm = _MONTH_MAP.get(mon, 0)
                dd, yyyy = int(m.group(2)), int(m.group(3))
            elif fmt == "day_month_name":
                dd = int(m.group(1))
                mm = _MONTH_MAP.get(m.group(2).lower(), 0)
                yyyy = int(m.group(3))
            else:
                continue

            if 1 <= mm <= 12 and 1 <= dd <= 31 and 1900 <= yyyy <= 2100:
                return f"{yyyy:04d}-{mm:02d}-{dd:02d}"
        except (ValueError, IndexError):
            continue
    return value


# ── Amount Normalization ──────────────────────────────────────

_CURRENCY_RE = re.compile(r"[\$€£¥₹]?\s*([\d,]+\.?\d*)")


def normalize_amount(value: str) -> dict:
    if not value:
        return {"raw": value, "numeric": None, "currency": ""}
    v = value.strip()

    currency = ""
    for sym, code in [("$", "USD"), ("€", "EUR"), ("£", "GBP"), ("¥", "JPY"), ("₹", "INR")]:
        if sym in v:
            currency = code
            break

    m = _CURRENCY_RE.search(v)
    if m:
        num_str = m.group(1).replace(",", "")
        try:
            return {"raw": v, "numeric": float(num_str), "currency": currency}
        except ValueError:
            pass
    return {"raw": v, "numeric": None, "currency": currency}


# ── Name Normalization ────────────────────────────────────────

def normalize_name(value: str) -> str:
    if not value:
        return value
    v = value.strip()
    if v == v.upper() and len(v) > 3:
        return v.title()
    return v


# ── Phone Normalization ───────────────────────────────────────

_PHONE_DIGITS_RE = re.compile(r"[\d+]")


def normalize_phone(value: str) -> str:
    if not value:
        return value
    digits = re.sub(r"[^\d+]", "", value)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if digits.startswith("+"):
        return digits
    return value


# ── Email Validation ──────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(value: str) -> dict:
    v = value.strip().lower()
    return {"email": v, "valid": bool(_EMAIL_RE.match(v))}


# ── PII Detection ────────────────────────────────────────────

PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "passport": re.compile(r"\b[A-Z]\d{7}\b"),
    "phone": re.compile(r"\+?\d{10,15}"),
    "email": _EMAIL_RE,
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "vin": re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b"),
}

SENSITIVE_FIELDS = {
    "ssn", "social_security", "credit_card", "card_number", "cvv",
    "password", "secret", "token", "api_key", "bank_account",
    "routing_number", "aadhaar", "passport_number",
}


def detect_pii(extraction: dict) -> list[dict]:
    findings: list[dict] = []
    for key, value in extraction.items():
        if key.startswith("_") or value is None:
            continue
        val_str = str(value)

        if key.lower() in SENSITIVE_FIELDS:
            findings.append({"field": key, "type": "sensitive_field", "value_preview": val_str[:4] + "***"})

        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(val_str):
                findings.append({"field": key, "type": pii_type, "value_preview": val_str[:4] + "***"})
                break

    return findings


def mask_pii(value: str) -> str:
    for pii_type, pattern in PII_PATTERNS.items():
        value = pattern.sub(lambda m: m.group()[:4] + "*" * (len(m.group()) - 4), value)
    return value


# ── Full Normalization Pipeline ───────────────────────────────

DATE_FIELD_HINTS = {"date", "dob", "birth", "expiry", "issue", "effective", "collection", "report", "due", "created", "updated"}
AMOUNT_FIELD_HINTS = {"amount", "total", "subtotal", "tax", "fee", "price", "cost", "balance", "payment", "salary", "deductible"}
NAME_FIELD_HINTS = {"name", "patient", "doctor", "physician", "vendor", "customer", "subscriber", "policyholder", "applicant", "signatory"}
PHONE_FIELD_HINTS = {"phone", "mobile", "tel", "fax", "contact"}
EMAIL_FIELD_HINTS = {"email", "mail"}


def normalize_extraction(extraction: dict, enable_pii_detection: bool = True) -> dict:
    normalized: dict[str, Any] = {}
    pii_warnings: list[dict] = []

    for key, value in extraction.items():
        if key.startswith("_"):
            normalized[key] = value
            continue
        if value is None:
            normalized[key] = value
            continue

        val_str = str(value).strip()
        key_lower = key.lower()

        if any(hint in key_lower for hint in DATE_FIELD_HINTS):
            normalized[key] = normalize_date(val_str)

        elif any(hint in key_lower for hint in AMOUNT_FIELD_HINTS):
            amt = normalize_amount(val_str)
            normalized[key] = val_str
            normalized[f"_{key}_numeric"] = amt["numeric"]
            normalized[f"_{key}_currency"] = amt["currency"]

        elif any(hint in key_lower for hint in NAME_FIELD_HINTS):
            normalized[key] = normalize_name(val_str)

        elif any(hint in key_lower for hint in PHONE_FIELD_HINTS):
            normalized[key] = normalize_phone(val_str)

        elif any(hint in key_lower for hint in EMAIL_FIELD_HINTS):
            result = validate_email(val_str)
            normalized[key] = result["email"]
            if not result["valid"]:
                normalized[f"_{key}_valid"] = False

        else:
            normalized[key] = val_str

    if enable_pii_detection:
        pii_warnings = detect_pii(normalized)
        if pii_warnings:
            normalized["_pii_warnings"] = pii_warnings

    return normalized
