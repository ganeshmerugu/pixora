from __future__ import annotations
import re
from pixora.agents.state import AgentState


class ValidationIssue:
    def __init__(self, field: str, dimension: str, message: str, severity: str = "warning"):
        self.field = field
        self.dimension = dimension
        self.message = message
        self.severity = severity

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "dimension": self.dimension,
            "message": self.message,
            "severity": self.severity,
        }


class ValidatorAgent:
    async def run(self, state: AgentState) -> AgentState:
        extraction = state.get("extraction_result", {})
        schema = state.get("extraction_schema", {})
        doc_tree = state.get("document_tree", {})

        issues: list[dict] = []

        issues.extend(self._check_schema_compliance(extraction, schema))
        issues.extend(self._check_completeness(extraction, schema))
        issues.extend(self._check_type_accuracy(extraction, schema))
        issues.extend(self._check_source_grounding(extraction, doc_tree))
        issues.extend(self._check_cross_field(extraction, state.get("profile", {})))

        errors = [i for i in issues if i["severity"] == "error"]
        passed = len(errors) == 0

        state["validator_issues"] = issues
        state["validation_passed"] = passed

        state.setdefault("decision_trace", []).append({
            "agent": "validator",
            "issues_count": len(issues),
            "errors": len(errors),
            "passed": passed,
        })

        return state

    def _check_schema_compliance(self, extraction: dict, schema: dict) -> list[dict]:
        issues: list[dict] = []
        for node in schema.get("nodes", []):
            name = node["name"]
            if node.get("required", False) and (name not in extraction or extraction[name] is None):
                issues.append(ValidationIssue(
                    field=name, dimension="schema_compliance",
                    message=f"Required field '{name}' is missing", severity="error",
                ).to_dict())
        return issues

    def _check_completeness(self, extraction: dict, schema: dict) -> list[dict]:
        issues: list[dict] = []
        nodes = schema.get("nodes", [])
        if not nodes:
            return issues

        expected = len(nodes)
        filled = sum(1 for n in nodes if extraction.get(n["name"]) is not None)

        if expected > 0 and filled / expected < 0.5:
            issues.append(ValidationIssue(
                field="*", dimension="completeness",
                message=f"Only {filled}/{expected} fields extracted ({filled/expected:.0%})",
                severity="warning",
            ).to_dict())

        return issues

    def _check_type_accuracy(self, extraction: dict, schema: dict) -> list[dict]:
        issues: list[dict] = []
        for node in schema.get("nodes", []):
            name = node["name"]
            value = extraction.get(name)
            if value is None:
                continue

            field_type = node.get("field_type", "STRING")
            if field_type == "NUMBER":
                try:
                    float(str(value).replace(",", "").replace("$", ""))
                except ValueError:
                    issues.append(ValidationIssue(
                        field=name, dimension="type_accuracy",
                        message=f"Field '{name}' expected NUMBER, got '{value}'", severity="warning",
                    ).to_dict())
            elif field_type == "DATE":
                if not re.search(r"\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4}", str(value)):
                    issues.append(ValidationIssue(
                        field=name, dimension="type_accuracy",
                        message=f"Field '{name}' expected DATE format, got '{value}'", severity="warning",
                    ).to_dict())

            for rule in node.get("validation_rules", []):
                if rule["type"] == "regex":
                    pattern = rule["params"].get("pattern", "")
                    if pattern and not re.search(pattern, str(value)):
                        issues.append(ValidationIssue(
                            field=name, dimension="ontology_compliance",
                            message=rule.get("message", f"Field '{name}' failed regex validation"),
                            severity="warning",
                        ).to_dict())

        return issues

    def _check_cross_field(self, extraction: dict, profile: dict) -> list[dict]:
        issues: list[dict] = []
        doc_type = profile.get("doc_type", "")

        if doc_type in ("invoice", "receipt"):
            subtotal = self._parse_currency(extraction.get("subtotal"))
            tax = self._parse_currency(extraction.get("tax"))
            total = self._parse_currency(extraction.get("total_due") or extraction.get("total"))

            if subtotal is not None and tax is not None and total is not None:
                expected_total = subtotal + tax
                tolerance = max(total * 0.02, 0.01)
                if abs(expected_total - total) > tolerance:
                    issues.append(ValidationIssue(
                        field="total_due", dimension="cross_field",
                        message=f"subtotal ({subtotal}) + tax ({tax}) = {expected_total:.2f}, but total_due = {total:.2f}",
                        severity="warning",
                    ).to_dict())

            due_date = extraction.get("due_date")
            inv_date = extraction.get("invoice_date")
            if due_date and inv_date:
                due_parsed = self._parse_date_loose(due_date)
                inv_parsed = self._parse_date_loose(inv_date)
                if due_parsed and inv_parsed and due_parsed < inv_parsed:
                    issues.append(ValidationIssue(
                        field="due_date", dimension="cross_field",
                        message=f"due_date '{due_date}' is before invoice_date '{inv_date}'",
                        severity="warning",
                    ).to_dict())

        if doc_type == "medical":
            collection = extraction.get("collection_date")
            report = extraction.get("report_date")
            if collection and report:
                c_parsed = self._parse_date_loose(collection)
                r_parsed = self._parse_date_loose(report)
                if c_parsed and r_parsed and r_parsed < c_parsed:
                    issues.append(ValidationIssue(
                        field="report_date", dimension="cross_field",
                        message=f"report_date '{report}' is before collection_date '{collection}'",
                        severity="warning",
                    ).to_dict())

        if doc_type == "contract":
            eff = extraction.get("effective_date")
            exp = extraction.get("expiration_date")
            if eff and exp:
                eff_parsed = self._parse_date_loose(eff)
                exp_parsed = self._parse_date_loose(exp)
                if eff_parsed and exp_parsed and exp_parsed < eff_parsed:
                    issues.append(ValidationIssue(
                        field="expiration_date", dimension="cross_field",
                        message=f"expiration_date '{exp}' is before effective_date '{eff}'",
                        severity="warning",
                    ).to_dict())

        return issues

    def _parse_currency(self, value) -> float | None:
        if value is None:
            return None
        text = str(value).strip()
        cleaned = re.sub(r"[^\d.\-]", "", text)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_date_loose(self, value: str) -> tuple | None:
        m = re.search(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", str(value))
        if m:
            a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if c < 100:
                c += 2000
            if a > 31:
                return (a, b, c)
            return (c, a, b)
        return None

    def _check_source_grounding(self, extraction: dict, doc_tree: dict) -> list[dict]:
        issues: list[dict] = []
        all_text = ""
        for page in doc_tree.get("pages", []):
            for region in page.get("regions", []):
                all_text += " " + region.get("content", "")
        all_text_lower = all_text.lower()

        for field, value in extraction.items():
            if value is None:
                continue
            val_str = str(value).strip().lower()
            if val_str and len(val_str) > 2 and val_str not in all_text_lower:
                issues.append(ValidationIssue(
                    field=field, dimension="grounding",
                    message=f"Value '{value}' for field '{field}' not found in source text",
                    severity="warning",
                ).to_dict())

        return issues
