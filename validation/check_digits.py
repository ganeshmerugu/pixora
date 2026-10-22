"""Check-digit verification for structured identifiers.

Supports: Luhn (credit cards, IMEI), IBAN (mod-97), US SSN format,
US EIN format, and generic modulus checks.
"""
from __future__ import annotations
import re
from typing_extensions import Required, TypedDict


class ValidationResult(TypedDict, total=False):
    field: Required[str]
    value: Required[str]
    valid: Required[bool]
    check_type: str
    message: str


def luhn_check(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 2:
        return False

    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_check(iban: str) -> bool:
    cleaned = iban.replace(" ", "").replace("-", "").upper()
    if len(cleaned) < 5 or not cleaned[:2].isalpha() or not cleaned[2:4].isdigit():
        return False

    rearranged = cleaned[4:] + cleaned[:4]

    numeric = []
    for c in rearranged:
        if c.isdigit():
            numeric.append(c)
        elif c.isalpha():
            numeric.append(str(ord(c) - ord("A") + 10))
        else:
            return False

    number = int("".join(numeric))
    return number % 97 == 1


def mod97_check(number: str) -> bool:
    digits = number.replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) < 2:
        return False
    return int(digits) % 97 == 1


def credit_card_check(number: str) -> bool:
    digits_only = re.sub(r"[\s\-]", "", number)
    if not digits_only.isdigit() or len(digits_only) < 13 or len(digits_only) > 19:
        return False
    return luhn_check(digits_only)


def ssn_format_check(ssn: str) -> bool:
    cleaned = ssn.replace("-", "").replace(" ", "")
    if len(cleaned) != 9 or not cleaned.isdigit():
        return False
    area = int(cleaned[:3])
    group = int(cleaned[3:5])
    serial = int(cleaned[5:])
    if area == 0 or area == 666 or area >= 900:
        return False
    if group == 0 or serial == 0:
        return False
    return True


def ein_format_check(ein: str) -> bool:
    cleaned = ein.replace("-", "").replace(" ", "")
    if len(cleaned) != 9 or not cleaned.isdigit():
        return False
    prefix = int(cleaned[:2])
    valid_prefixes = set(range(1, 7)) | set(range(10, 17)) | {20, 21, 22, 23, 24, 25, 26, 27}
    valid_prefixes |= set(range(30, 40)) | set(range(40, 49)) | set(range(50, 69))
    valid_prefixes |= set(range(68, 78)) | set(range(80, 89)) | {90, 91, 92, 93, 94, 95, 98, 99}
    return prefix in valid_prefixes


_FIELD_CHECKS: dict[str, list[str]] = {
    "credit_card": ["luhn", "credit_card"],
    "card_number": ["luhn", "credit_card"],
    "iban": ["iban"],
    "bank_account": ["iban"],
    "ssn": ["ssn"],
    "social_security": ["ssn"],
    "ein": ["ein"],
    "employer_id": ["ein"],
    "imei": ["luhn"],
}

_CHECK_FUNCTIONS = {
    "luhn": lambda v: luhn_check(v),
    "credit_card": lambda v: credit_card_check(v),
    "iban": lambda v: iban_check(v),
    "mod97": lambda v: mod97_check(v),
    "ssn": lambda v: ssn_format_check(v),
    "ein": lambda v: ein_format_check(v),
}


def verify_field(field_name: str, value: str) -> ValidationResult:
    field_lower = field_name.lower().replace(" ", "_")

    checks: list[str] = []
    for pattern, check_list in _FIELD_CHECKS.items():
        if pattern in field_lower:
            checks = check_list
            break

    if not checks:
        if re.match(r"^[A-Z]{2}\d{2}\s?[A-Z0-9\s]{10,30}$", value.strip()):
            checks = ["iban"]
        elif re.match(r"^[\d\s\-]{13,19}$", value.strip()) and len(re.sub(r"\D", "", value)) >= 13:
            checks = ["luhn"]

    if not checks:
        return ValidationResult(field=field_name, value=value, valid=True, message="no_check_applicable")

    for check_name in checks:
        func = _CHECK_FUNCTIONS.get(check_name)
        if func and not func(value):
            return ValidationResult(
                field=field_name, value=value, valid=False,
                check_type=check_name, message=f"failed_{check_name}_check",
            )

    return ValidationResult(
        field=field_name, value=value, valid=True,
        check_type=checks[0], message="passed",
    )


def verify_all(fields: dict[str, str]) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for field_name, value in fields.items():
        if not value or not isinstance(value, str):
            continue
        result = verify_field(field_name, value)
        if result.get("check_type"):
            results.append(result)
    return results
