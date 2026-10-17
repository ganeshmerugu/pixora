from __future__ import annotations
import pytest
from pixora.agents.state import AgentState
from pixora.agents.classifier import ClassifierAgent
from pixora.agents.router import RouterAgent, build_processing_plan
from pixora.agents.extractor import ExtractorAgent
from pixora.agents.validator import ValidatorAgent
from pixora.agents.scorer import ScorerAgent, adaptive_threshold
from pixora.agents.supervisor import SupervisorAgent
from pixora.models.pipeline import DocumentProfile
from pixora.models.document import DocumentTree, Page, Region


def _base_state(**overrides) -> AgentState:
    s = AgentState(document_id="doc1", job_id="job1")
    s.update(overrides)
    return s


def _state_with_doc_tree(text: str = "Invoice Number: INV-001\nTotal Due: $500.00") -> AgentState:
    tree = DocumentTree(
        document_id="doc1",
        pages=[Page(page_number=1, regions=[Region(id="r1", type="TEXT", content=text)])],
    )
    return _base_state(
        source_filename="invoice.pdf",
        document_tree=dict(tree),
        extraction_schema={
            "nodes": [
                {"name": "invoice_number", "field_type": "STRING", "required": True},
                {"name": "total", "field_type": "NUMBER"},
            ]
        },
    )


# --- Classifier Agent ---

@pytest.mark.asyncio
async def test_classifier_sets_profile():
    state = _base_state(source_filename="invoice.pdf")
    agent = ClassifierAgent()
    state = await agent.run(state)
    assert "profile" in state
    assert state["profile"]["doc_type"] is not None


@pytest.mark.asyncio
async def test_classifier_uses_doc_tree_text():
    state = _state_with_doc_tree("INVOICE\nInvoice Number: INV-001\nBill To: Acme\nTotal Due: $500")
    agent = ClassifierAgent()
    state = await agent.run(state)
    assert state["profile"]["doc_type"] == "invoice"


@pytest.mark.asyncio
async def test_classifier_adds_decision_trace():
    state = _base_state(source_filename="report.pdf")
    agent = ClassifierAgent()
    state = await agent.run(state)
    assert any(d["agent"] == "classifier" for d in state.get("decision_trace", []))


# --- Router Agent ---

def test_build_plan_scanned_handwriting():
    profile = DocumentProfile(doc_type="form", confidence=0.8, is_scanned=True, has_handwriting=True)
    plan = build_processing_plan(profile)
    assert plan["ocr_strategy"] == "CLAUDE_VISION_PRIMARY"
    assert plan["extraction_mode"] == "deep"


def test_build_plan_simple_native():
    profile = DocumentProfile(doc_type="letter", confidence=0.8, is_scanned=False, complexity=0.2, has_tables=False)
    plan = build_processing_plan(profile)
    assert plan["ocr_strategy"] == "TEXT_DIRECT"
    assert plan["extraction_mode"] == "fast"


def test_build_plan_scanned_standard():
    profile = DocumentProfile(doc_type="invoice", confidence=0.8, is_scanned=True)
    plan = build_processing_plan(profile)
    assert plan["ocr_strategy"] == "ENSEMBLE"


@pytest.mark.asyncio
async def test_router_sets_plan():
    state = _base_state(profile=DocumentProfile(doc_type="invoice", confidence=0.9, is_scanned=True))
    agent = RouterAgent()
    state = await agent.run(state)
    assert "processing_plan" in state
    assert state["processing_plan"]["ocr_strategy"] == "ENSEMBLE"


@pytest.mark.asyncio
async def test_router_handles_missing_profile():
    state = _base_state()
    agent = RouterAgent()
    state = await agent.run(state)
    assert "processing_plan" in state


# --- Extractor Agent ---

@pytest.mark.asyncio
async def test_extractor_basic_extraction():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: $500.00")
    agent = ExtractorAgent()
    state = await agent.run(state)
    result = state["extraction_result"]
    assert result.get("invoice_number") == "INV-001"


@pytest.mark.asyncio
async def test_extractor_no_schema():
    state = _base_state(document_tree={"pages": [{"regions": [{"content": "hello"}]}]}, extraction_schema={})
    agent = ExtractorAgent()
    state = await agent.run(state)
    assert state["extraction_result"] == {}


@pytest.mark.asyncio
async def test_extractor_missing_field():
    state = _state_with_doc_tree("Some random text with no fields")
    agent = ExtractorAgent()
    state = await agent.run(state)
    assert state["extraction_result"]["invoice_number"] is None


# --- Validator Agent ---

@pytest.mark.asyncio
async def test_validator_passes_clean_extraction():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: 500")
    state["extraction_result"] = {"invoice_number": "INV-001", "total": "500"}
    agent = ValidatorAgent()
    state = await agent.run(state)
    assert state["validation_passed"] is True


@pytest.mark.asyncio
async def test_validator_catches_missing_required():
    state = _state_with_doc_tree()
    state["extraction_result"] = {"invoice_number": None, "total": "500"}
    state["extraction_schema"]["nodes"][0]["required"] = True
    agent = ValidatorAgent()
    state = await agent.run(state)
    assert state["validation_passed"] is False
    errors = [i for i in state["validator_issues"] if i["severity"] == "error"]
    assert len(errors) >= 1


@pytest.mark.asyncio
async def test_validator_catches_ungrounded_value():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: $500.00")
    state["extraction_result"] = {"invoice_number": "INV-001", "total": "HALLUCINATED_VALUE_999"}
    agent = ValidatorAgent()
    state = await agent.run(state)
    grounding = [i for i in state["validator_issues"] if i["dimension"] == "grounding"]
    assert len(grounding) >= 1


@pytest.mark.asyncio
async def test_validator_type_check_number():
    state = _state_with_doc_tree("Total: not_a_number")
    state["extraction_result"] = {"invoice_number": "INV-001", "total": "not_a_number"}
    agent = ValidatorAgent()
    state = await agent.run(state)
    type_issues = [i for i in state["validator_issues"] if i["dimension"] == "type_accuracy"]
    assert len(type_issues) >= 1


@pytest.mark.asyncio
async def test_validator_regex_rule():
    state = _state_with_doc_tree("Invoice Number: ABC\nTotal: 500")
    state["extraction_schema"]["nodes"][0]["validation_rules"] = [
        {"type": "regex", "params": {"pattern": r"^INV-\d+"}, "message": "Must match INV-NNN"}
    ]
    state["extraction_result"] = {"invoice_number": "ABC", "total": "500"}
    agent = ValidatorAgent()
    state = await agent.run(state)
    ontology = [i for i in state["validator_issues"] if i["dimension"] == "ontology_compliance"]
    assert len(ontology) >= 1


# --- Scorer Agent ---

def test_adaptive_threshold_simple():
    profile = {"complexity": 0.3, "has_tables": False, "has_handwriting": False}
    t = adaptive_threshold(profile)
    assert 0.65 <= t <= 0.90


def test_adaptive_threshold_complex():
    profile = {"complexity": 0.8, "has_tables": True, "has_handwriting": True}
    t = adaptive_threshold(profile)
    assert t < 0.80


@pytest.mark.asyncio
async def test_scorer_produces_report():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: 500")
    state["extraction_result"] = {"invoice_number": "INV-001", "total": "500"}
    state["validator_issues"] = []
    state["profile"] = DocumentProfile(doc_type="invoice", confidence=0.9)
    agent = ScorerAgent()
    state = await agent.run(state)
    assert "quality_report" in state
    assert state["quality_score"] > 0
    assert state["recommendation"] in ("accept", "human_review", "reprocess")


@pytest.mark.asyncio
async def test_scorer_accept_on_good_extraction():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: 500")
    state["extraction_result"] = {"invoice_number": "INV-001", "total": "500"}
    state["validator_issues"] = []
    state["profile"] = DocumentProfile(doc_type="invoice", confidence=0.9, complexity=0.2)
    agent = ScorerAgent()
    state = await agent.run(state)
    assert state["recommendation"] == "accept"


@pytest.mark.asyncio
async def test_scorer_reprocess_on_bad_extraction():
    state = _state_with_doc_tree("Invoice Number: INV-001\nTotal: 500")
    state["extraction_result"] = {"invoice_number": None, "total": None}
    state["validator_issues"] = [
        {"severity": "error", "dimension": "schema_compliance", "message": "missing", "field": "invoice_number"},
        {"severity": "warning", "dimension": "grounding", "message": "ungrounded", "field": "total"},
    ]
    state["profile"] = DocumentProfile(doc_type="invoice", confidence=0.9)
    agent = ScorerAgent()
    state = await agent.run(state)
    assert state["recommendation"] in ("human_review", "reprocess")


# --- Supervisor (end-to-end) ---

@pytest.mark.asyncio
async def test_supervisor_end_to_end():
    state = _base_state(
        source_filename="invoice.pdf",
        document_tree={
            "pages": [{"regions": [{"content": "Invoice Number: INV-001\nBill To: Acme\nTotal Due: $500"}]}]
        },
        extraction_schema={
            "nodes": [
                {"name": "invoice_number", "field_type": "STRING"},
                {"name": "total", "field_type": "NUMBER"},
            ]
        },
    )
    supervisor = SupervisorAgent()
    state = await supervisor.run(state)

    assert "profile" in state
    assert "processing_plan" in state
    assert "extraction_result" in state
    assert "quality_report" in state
    assert "verification_report" in state
    assert state["verification_report"]["total_rounds"] >= 1


@pytest.mark.asyncio
async def test_supervisor_tracks_hypotheses():
    state = _base_state(
        source_filename="doc.pdf",
        document_tree={"pages": [{"regions": [{"content": "Some doc text"}]}]},
        extraction_schema={"nodes": [{"name": "title", "field_type": "STRING"}]},
    )
    supervisor = SupervisorAgent()
    state = await supervisor.run(state)
    assert len(state["task_hypotheses"]) >= 1
    assert state["task_hypotheses"][0]["round_num"] == 0
