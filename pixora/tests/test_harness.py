from __future__ import annotations
import pytest
from pixora.harness.grounding import GroundingVerifier
from pixora.harness.cost_governor import CostGovernor
from pixora.harness.drift_detector import DriftDetector
from pixora.harness.intervention import InterventionLogger
from pixora.harness.trace_models import build_verification_report
from pixora.harness.verification import build_report_from_state


DOC_TREE = {
    "pages": [{
        "page_number": 1,
        "regions": [
            {"id": "r1", "content": "Invoice Number: INV-2024-001\nVendor: Acme Corp\nTotal Due: $1,500.00", "bbox": {}},
        ],
    }]
}


# --- C12 GroundingVerifier ---

def test_grounding_exact_match():
    v = GroundingVerifier()
    report = v.verify({"invoice_number": "INV-2024-001"}, DOC_TREE, "doc1")
    assert report["grounded_count"] == 1
    assert report["ungrounded_count"] == 0
    assert report["grounding_rate"] == 1.0


def test_grounding_case_insensitive():
    v = GroundingVerifier()
    report = v.verify({"vendor": "acme corp"}, DOC_TREE, "doc1")
    assert report["grounded_count"] == 1


def test_grounding_hallucinated_value():
    v = GroundingVerifier()
    report = v.verify({"vendor": "Nonexistent Company LLC"}, DOC_TREE, "doc1")
    assert report["ungrounded_count"] == 1
    assert "vendor" in report["flagged_hallucinations"]


def test_grounding_numeric_match():
    v = GroundingVerifier()
    report = v.verify({"total": "$1,500.00"}, DOC_TREE, "doc1")
    assert report["grounded_count"] == 1


def test_grounding_mixed():
    v = GroundingVerifier()
    report = v.verify(
        {"invoice_number": "INV-2024-001", "vendor": "HALLUCINATED"},
        DOC_TREE, "doc1",
    )
    assert report["grounded_count"] == 1
    assert report["ungrounded_count"] == 1
    assert 0.0 < report["grounding_rate"] < 1.0


def test_grounding_null_values_skipped():
    v = GroundingVerifier()
    report = v.verify({"field1": None, "field2": ""}, DOC_TREE, "doc1")
    assert report["total_fields"] == 0


# --- C14 CostGovernor ---

def test_cost_governor_proceed():
    gov = CostGovernor(budget_tokens=100_000)
    d = gov.check("extract", estimated_tokens=5000)
    assert d["action"] == "proceed"


def test_cost_governor_halt():
    gov = CostGovernor(budget_tokens=100)
    gov.record_usage(100)
    d = gov.check("extract", estimated_tokens=50)
    assert d["action"] == "halt"


def test_cost_governor_skip_when_quality_ok():
    gov = CostGovernor(budget_tokens=1000)
    gov.record_usage(900)
    d = gov.check("correction", estimated_tokens=500, quality_so_far=0.85)
    assert d["action"] == "skip"


def test_cost_governor_downgrade():
    gov = CostGovernor(budget_tokens=1000)
    gov.record_usage(800)
    d = gov.check("extract", estimated_tokens=300, quality_so_far=0.5)
    assert d["action"] == "downgrade"


def test_cost_governor_report():
    gov = CostGovernor(budget_tokens=50_000)
    gov.record_usage(10_000)
    gov.check("extract", 5000)
    report = gov.get_report("doc1", fields_extracted=5)
    assert report["total_tokens"] == 10_000
    assert report["total_cost_usd"] > 0
    assert report["cost_per_field"] > 0


def test_cost_governor_remaining():
    gov = CostGovernor(budget_tokens=1000)
    gov.record_usage(400)
    assert gov.remaining == 600
    assert gov.consumed == 400


# --- C10 DriftDetector ---

def test_drift_no_alerts_when_stable():
    detector = DriftDetector(baselines={"grounding_rate": 0.95, "completeness": 0.90})
    reports = [
        {"quality_report": {"grounding_score": 0.94, "completeness": 0.89, "recommendation": "accept"}},
        {"quality_report": {"grounding_score": 0.93, "completeness": 0.88, "recommendation": "accept"}},
    ]
    result = detector.detect(reports, "batch1")
    assert result["status"] == "ok"


def test_drift_warns_on_grounding_drop():
    detector = DriftDetector(baselines={"grounding_rate": 0.95})
    reports = [
        {"quality_report": {"grounding_score": 0.90, "recommendation": "accept"}},
        {"quality_report": {"grounding_score": 0.90, "recommendation": "accept"}},
    ]
    result = detector.detect(reports, "batch2")
    warn_alerts = [a for a in result["alerts"] if a["metric"] == "grounding_rate"]
    assert len(warn_alerts) >= 1


def test_drift_alerts_on_severe_drop():
    detector = DriftDetector(baselines={"grounding_rate": 0.95})
    reports = [
        {"quality_report": {"grounding_score": 0.80, "recommendation": "accept"}},
    ]
    result = detector.detect(reports, "batch3")
    alerts = [a for a in result["alerts"] if a["level"] == "alert"]
    assert len(alerts) >= 1
    assert result["status"] == "alert"


def test_drift_empty_reports():
    detector = DriftDetector()
    result = detector.detect([], "empty")
    assert result["status"] == "ok"
    assert result["document_count"] == 0


def test_drift_set_baselines_from_batch():
    detector = DriftDetector()
    baseline_reports = [
        {"quality_report": {"grounding_score": 0.95, "completeness": 0.90, "recommendation": "accept"}},
    ]
    detector.set_baselines_from_batch(baseline_reports)
    assert "grounding_rate" in detector.baselines


# --- C11 InterventionLogger ---

def test_intervention_log_and_retrieve():
    logger = InterventionLogger()
    logger.log("doc1", "vendor", "field_value_changed", machine_value="Acm", human_value="Acme")
    interventions = logger.get_interventions("doc1")
    assert len(interventions) == 1
    assert interventions[0]["gap_category"].startswith("C13")


def test_intervention_aggregate_gaps():
    logger = InterventionLogger()
    logger.log("doc1", "vendor", "field_value_changed")
    logger.log("doc2", "total", "field_value_changed")
    logger.log("doc3", "type", "doc_type_changed")
    gaps = logger.aggregate_gaps()
    assert len(gaps) >= 2


def test_intervention_top_fields():
    logger = InterventionLogger()
    logger.log("d1", "vendor", "field_value_changed")
    logger.log("d2", "vendor", "field_value_changed")
    logger.log("d3", "total", "field_added")
    top = logger.top_corrected_fields(limit=5)
    assert top[0] == ("vendor", 2)


def test_intervention_gap_map_coverage():
    logger = InterventionLogger()
    for action in ["field_added", "field_removed", "field_value_changed", "table_structure_changed", "doc_type_changed", "schema_changed"]:
        logger.log("d1", "f", action)
    assert all("unknown_action" not in i["gap_category"] for i in logger.get_interventions())


def test_intervention_clear():
    logger = InterventionLogger()
    logger.log("d1", "f", "field_added")
    logger.clear()
    assert logger.get_interventions() == []


# --- Trace Models ---

def test_build_verification_report():
    report = build_verification_report(
        document_id="doc1", total_rounds=3, final_score=0.85,
        recommendation="accept", hypotheses=[{"round_num": 0}], attributions=[],
    )
    assert report["document_id"] == "doc1"
    assert report["total_rounds"] == 3


def test_build_report_from_state():
    state = {
        "document_id": "doc1", "correction_round": 2, "quality_score": 0.87,
        "recommendation": "accept", "task_hypotheses": [], "failure_attributions": [],
    }
    report = build_report_from_state(state)
    assert report["total_rounds"] == 3
    assert report["final_score"] == 0.87
