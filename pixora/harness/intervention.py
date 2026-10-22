from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from collections import Counter


class Intervention(TypedDict, total=False):
    document_id: Required[str]
    field: Required[str]
    action: Required[str]
    machine_value: str | None
    human_value: str | None
    gap_category: str
    metadata: dict[str, Any]


_GAP_MAP: dict[str, str] = {
    "field_added":             "C12_Grounding — field present but extraction missed it",
    "field_removed":           "C12_Grounding — hallucinated a field not in document",
    "field_value_changed":     "C13_OCRArbiter — wrong engine selected or OCR error",
    "table_structure_changed": "C3_DocumentDecomposer — table region mis-segmented",
    "doc_type_changed":        "C1_Classifier — wrong document type",
    "schema_changed":          "C6_Ontology — wrong extraction schema selected",
}


class InterventionLogger:
    def __init__(self) -> None:
        self._interventions: list[Intervention] = []

    def log(
        self,
        document_id: str,
        field: str,
        action: str,
        machine_value: str | None = None,
        human_value: str | None = None,
    ) -> Intervention:
        gap = _GAP_MAP.get(action, f"unknown_action: {action}")

        intervention = Intervention(
            document_id=document_id,
            field=field,
            action=action,
            machine_value=machine_value,
            human_value=human_value,
            gap_category=gap,
        )
        self._interventions.append(intervention)
        return intervention

    def get_interventions(self, document_id: str | None = None) -> list[Intervention]:
        if document_id:
            return [i for i in self._interventions if i["document_id"] == document_id]
        return list(self._interventions)

    def aggregate_gaps(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for i in self._interventions:
            counter[i.get("gap_category", "unknown")] += 1
        return dict(counter.most_common())

    def top_corrected_fields(self, limit: int = 10) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter()
        for i in self._interventions:
            counter[i["field"]] += 1
        return counter.most_common(limit)

    def clear(self) -> None:
        self._interventions.clear()
