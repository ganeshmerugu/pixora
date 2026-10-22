"""Math consistency validation for extracted financial documents.

Checks: subtotal + tax - discount = total, line_qty * unit_price = line_total,
sum of line totals = subtotal, percentage calculations.
"""
from __future__ import annotations
import re
from typing import Any
from typing_extensions import Required, TypedDict


class MathIssue(TypedDict, total=False):
    rule: Required[str]
    severity: Required[str]
    message: Required[str]
    expected: float
    actual: float
    difference: float
    fields_involved: list[str]
    suggested_correction: dict[str, float]


DEFAULT_TOLERANCE = 0.02


def _parse_amount(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^\d.\-,]", "", str(value))
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned and cleaned.count(",") == 1:
        parts = cleaned.split(",")
        if len(parts[1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_field(data: dict, *candidates: str) -> float | None:
    for key in candidates:
        for data_key, val in data.items():
            if key in data_key.lower().replace(" ", "_"):
                parsed = _parse_amount(val)
                if parsed is not None:
                    return parsed
    return None


class MathValidator:
    def __init__(self, tolerance: float = DEFAULT_TOLERANCE):
        self.tolerance = tolerance

    def validate(self, fields: dict[str, Any]) -> list[MathIssue]:
        issues: list[MathIssue] = []
        issues.extend(self._check_total_equation(fields))
        issues.extend(self._check_line_items(fields))
        issues.extend(self._check_tax_percentage(fields))
        issues.extend(self._check_discount(fields))
        return issues

    def _check_total_equation(self, fields: dict) -> list[MathIssue]:
        subtotal = _find_field(fields, "subtotal", "sub_total", "net_amount", "net_total")
        tax = _find_field(fields, "tax", "tax_amount", "vat", "gst", "sales_tax")
        discount = _find_field(fields, "discount", "discount_amount")
        total = _find_field(fields, "total", "total_amount", "grand_total", "amount_due", "balance_due")

        if total is None:
            return []

        if subtotal is not None and tax is not None:
            expected = subtotal + tax - (discount or 0.0)
            diff = abs(expected - total)
            if diff > self.tolerance:
                return [MathIssue(
                    rule="total_equation",
                    severity="error" if diff > 1.0 else "warning",
                    message=f"subtotal({subtotal}) + tax({tax}) - discount({discount or 0}) = {expected}, but total = {total}",
                    expected=round(expected, 2),
                    actual=total,
                    difference=round(diff, 2),
                    fields_involved=["subtotal", "tax", "discount", "total"],
                    suggested_correction={"total": round(expected, 2)},
                )]

        if subtotal is not None and tax is None and discount is None:
            if abs(subtotal - total) > self.tolerance:
                return [MathIssue(
                    rule="subtotal_equals_total",
                    severity="warning",
                    message=f"subtotal({subtotal}) != total({total}) but no tax/discount found",
                    expected=subtotal,
                    actual=total,
                    difference=round(abs(subtotal - total), 2),
                    fields_involved=["subtotal", "total"],
                )]

        return []

    def _check_line_items(self, fields: dict) -> list[MathIssue]:
        issues: list[MathIssue] = []
        line_items = fields.get("line_items") or fields.get("items") or fields.get("lines")
        if not isinstance(line_items, list):
            return []

        line_totals: list[float] = []
        for i, item in enumerate(line_items):
            if not isinstance(item, dict):
                continue

            qty = _find_field(item, "quantity", "qty", "count", "units")
            unit_price = _find_field(item, "unit_price", "price", "rate", "unit_cost")
            line_total = _find_field(item, "total", "amount", "line_total", "extended", "ext_price")

            if qty is not None and unit_price is not None and line_total is not None:
                expected = qty * unit_price
                diff = abs(expected - line_total)
                if diff > self.tolerance:
                    issues.append(MathIssue(
                        rule="line_item_multiplication",
                        severity="error" if diff > 1.0 else "warning",
                        message=f"Line {i+1}: qty({qty}) x price({unit_price}) = {expected}, but line_total = {line_total}",
                        expected=round(expected, 2),
                        actual=line_total,
                        difference=round(diff, 2),
                        fields_involved=[f"items[{i}].quantity", f"items[{i}].unit_price", f"items[{i}].total"],
                        suggested_correction={f"items[{i}].total": round(expected, 2)},
                    ))

            if line_total is not None:
                line_totals.append(line_total)

        subtotal = _find_field(fields, "subtotal", "sub_total", "net_amount")
        if subtotal is not None and line_totals:
            computed_subtotal = sum(line_totals)
            diff = abs(computed_subtotal - subtotal)
            if diff > self.tolerance:
                issues.append(MathIssue(
                    rule="line_items_sum",
                    severity="error" if diff > 1.0 else "warning",
                    message=f"sum(line_totals) = {round(computed_subtotal, 2)}, but subtotal = {subtotal}",
                    expected=round(computed_subtotal, 2),
                    actual=subtotal,
                    difference=round(diff, 2),
                    fields_involved=["line_items", "subtotal"],
                    suggested_correction={"subtotal": round(computed_subtotal, 2)},
                ))

        return issues

    def _check_tax_percentage(self, fields: dict) -> list[MathIssue]:
        subtotal = _find_field(fields, "subtotal", "sub_total", "net_amount")
        tax = _find_field(fields, "tax", "tax_amount", "vat_amount")
        tax_rate = _find_field(fields, "tax_rate", "vat_rate", "tax_percent", "gst_rate")

        if subtotal is None or tax is None or tax_rate is None or subtotal == 0:
            return []

        rate = tax_rate if tax_rate > 1 else tax_rate * 100
        expected_tax = subtotal * (rate / 100.0)
        diff = abs(expected_tax - tax)

        if diff > self.tolerance:
            return [MathIssue(
                rule="tax_percentage",
                severity="warning",
                message=f"subtotal({subtotal}) x rate({rate}%) = {round(expected_tax, 2)}, but tax = {tax}",
                expected=round(expected_tax, 2),
                actual=tax,
                difference=round(diff, 2),
                fields_involved=["subtotal", "tax_rate", "tax_amount"],
                suggested_correction={"tax_amount": round(expected_tax, 2)},
            )]
        return []

    def _check_discount(self, fields: dict) -> list[MathIssue]:
        subtotal = _find_field(fields, "subtotal", "sub_total")
        discount = _find_field(fields, "discount", "discount_amount")
        discount_pct = _find_field(fields, "discount_rate", "discount_percent", "discount_pct")

        if subtotal is None or discount is None or discount_pct is None or subtotal == 0:
            return []

        rate = discount_pct if discount_pct > 1 else discount_pct * 100
        expected_disc = subtotal * (rate / 100.0)
        diff = abs(expected_disc - discount)

        if diff > self.tolerance:
            return [MathIssue(
                rule="discount_percentage",
                severity="warning",
                message=f"subtotal({subtotal}) x discount_rate({rate}%) = {round(expected_disc, 2)}, but discount = {discount}",
                expected=round(expected_disc, 2),
                actual=discount,
                difference=round(diff, 2),
                fields_involved=["subtotal", "discount_rate", "discount"],
                suggested_correction={"discount": round(expected_disc, 2)},
            )]
        return []
