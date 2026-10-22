from __future__ import annotations
from pixora.harness.trace_models import build_verification_report, VerificationReport


def build_report_from_state(state: dict) -> VerificationReport:
    return build_verification_report(
        document_id=state.get("document_id", ""),
        total_rounds=state.get("correction_round", 0) + 1,
        final_score=state.get("quality_score", 0.0),
        recommendation=state.get("recommendation", "unknown"),
        hypotheses=state.get("task_hypotheses", []),
        attributions=state.get("failure_attributions", []),
        grounding=state.get("grounding_report"),
        cost=state.get("cost_report"),
    )
