from __future__ import annotations
from pixora.agents.state import AgentState
from pixora.models.quality import ParseQualityReport, QualityIssue
from pixora.config.harness import DIMENSION_WEIGHTS, HARNESS_CONFIG


def adaptive_threshold(profile: dict, base: float = 0.80, floor: float = 0.65, ceiling: float = 0.90) -> float:
    complexity = profile.get("complexity", 0.5)
    table_factor = 0.1 if profile.get("has_tables") else 0.0
    handwriting_factor = 0.15 if profile.get("has_handwriting") else 0.0
    total = min(complexity + table_factor + handwriting_factor, 1.0)
    return max(floor, min(ceiling, base - (total * 0.15)))


class ScorerAgent:
    async def run(self, state: AgentState) -> AgentState:
        extraction = state.get("extraction_result", {})
        schema = state.get("extraction_schema", {})
        validator_issues = state.get("validator_issues", [])
        doc_tree = state.get("document_tree", {})
        profile = state.get("profile", {})

        scores = self._compute_dimension_scores(extraction, schema, validator_issues, doc_tree)
        overall = self._weighted_average(scores)

        threshold = adaptive_threshold(
            profile,
            base=HARNESS_CONFIG["scoring"]["base_threshold"],
            floor=HARNESS_CONFIG["scoring"]["floor"],
            ceiling=HARNESS_CONFIG["scoring"]["ceiling"],
        )

        if overall >= threshold:
            recommendation = "accept"
        elif overall >= threshold - 0.1:
            recommendation = "human_review"
        else:
            recommendation = "reprocess"

        quality_issues: list[QualityIssue] = []
        for issue in validator_issues:
            quality_issues.append(QualityIssue(
                severity=issue.get("severity", "warning"),
                dimension=issue.get("dimension", "unknown"),
                message=issue.get("message", ""),
                field=issue.get("field", ""),
            ))

        report = ParseQualityReport(
            document_id=state["document_id"],
            overall_score=overall,
            completeness=scores.get("completeness", 0.0),
            accuracy_confidence=scores.get("value_accuracy", 0.0),
            grounding_score=scores.get("grounding", 0.0),
            layout_fidelity=scores.get("reading_order", 0.0),
            issues=quality_issues,
            recommendation=recommendation,
        )

        state["quality_report"] = dict(report)
        state["quality_score"] = overall
        state["recommendation"] = recommendation

        state.setdefault("decision_trace", []).append({
            "agent": "scorer",
            "overall_score": overall,
            "threshold": threshold,
            "recommendation": recommendation,
            "dimension_scores": scores,
        })

        return state

    def _compute_dimension_scores(
        self, extraction: dict, schema: dict, issues: list[dict], doc_tree: dict
    ) -> dict[str, float]:
        scores: dict[str, float] = {}
        nodes = schema.get("nodes", [])

        # Completeness
        if nodes:
            filled = sum(1 for n in nodes if extraction.get(n["name"]) is not None)
            scores["completeness"] = filled / len(nodes)
        else:
            scores["completeness"] = 1.0 if extraction else 0.0

        # Grounding
        grounding_issues = [i for i in issues if i.get("dimension") == "grounding"]
        total_fields = max(len(extraction), 1)
        scores["grounding"] = max(0.0, 1.0 - len(grounding_issues) / total_fields)

        # Value accuracy
        type_issues = [i for i in issues if i.get("dimension") == "type_accuracy"]
        scores["value_accuracy"] = max(0.0, 1.0 - len(type_issues) / total_fields)

        # Type accuracy (from validation rules)
        ontology_issues = [i for i in issues if i.get("dimension") == "ontology_compliance"]
        scores["type_accuracy"] = max(0.0, 1.0 - len(ontology_issues) / total_fields)

        # Cross-field
        cross_issues = [i for i in issues if i.get("dimension") == "cross_field"]
        scores["cross_field"] = max(0.0, 1.0 - len(cross_issues) * 0.25)

        # Table structure
        has_tables = any(
            r.get("type") == "TABLE"
            for p in doc_tree.get("pages", [])
            for r in p.get("regions", [])
        )
        if has_tables:
            table_metrics = extraction.get("__table_eval")
            if table_metrics and isinstance(table_metrics, dict):
                scores["table_structure"] = round(
                    table_metrics.get("row_f1", 0.8) * 0.4
                    + table_metrics.get("cell_accuracy", 0.8) * 0.3
                    + table_metrics.get("column_accuracy", 0.8) * 0.3,
                    4,
                )
            else:
                scores["table_structure"] = 0.8
        else:
            scores["table_structure"] = 1.0

        # Reading order — check if extracted fields appear in document order
        scores["reading_order"] = self._compute_reading_order_score(extraction, doc_tree)

        # Ontology compliance
        schema_issues = [i for i in issues if i.get("dimension") == "schema_compliance"]
        scores["ontology_compliance"] = 0.0 if schema_issues else 1.0

        return scores

    def _compute_reading_order_score(self, extraction: dict, doc_tree: dict) -> float:
        all_text = ""
        for page in doc_tree.get("pages", []):
            for region in page.get("regions", []):
                all_text += " " + region.get("content", "")
        all_text_lower = all_text.lower()

        if not all_text_lower.strip() or not extraction:
            return 1.0

        field_positions: list[int] = []
        for field, value in extraction.items():
            if field.startswith("__") or value is None:
                continue
            val_str = str(value).strip().lower()
            if len(val_str) > 2:
                pos = all_text_lower.find(val_str)
                if pos >= 0:
                    field_positions.append(pos)

        if len(field_positions) < 2:
            return 1.0

        concordant = 0
        discordant = 0
        n = len(field_positions)
        for i in range(n):
            for j in range(i + 1, n):
                if field_positions[i] < field_positions[j]:
                    concordant += 1
                elif field_positions[i] > field_positions[j]:
                    discordant += 1

        total = concordant + discordant
        if total == 0:
            return 1.0
        tau = (concordant - discordant) / total
        return round((tau + 1.0) / 2.0, 4)

    def _weighted_average(self, scores: dict[str, float]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for dim, score in scores.items():
            weight = DIMENSION_WEIGHTS.get(dim, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
