from __future__ import annotations
import pytest
from pixora.models.document import BoundingBox, Region, Page, DocumentTree
from pixora.models.pipeline import PipelineState, ProcessingPlan, CorrectionDelta, DocumentProfile
from pixora.models.ontology import OntologyNode, ExtractionSchema, ValidationRule
from pixora.models.quality import QualityIssue, ParseQualityReport
from pixora.models.registry import ModelRegistry

def test_region_required_fields():
    r = Region(id="r1", type="TEXT", content="hello")
    assert r["id"] == "r1"
    assert r["type"] == "TEXT"
    assert r["content"] == "hello"

def test_region_optional_fields():
    r = Region(id="r1", type="TEXT", content="hello", confidence=0.95)
    assert r["confidence"] == 0.95

def test_region_metadata_bag():
    r = Region(id="r1", type="TEXT", content="hello", metadata={"font": "Arial", "custom_field": 42})
    assert r["metadata"]["custom_field"] == 42

def test_document_tree_structure():
    tree = DocumentTree(document_id="doc1", pages=[Page(page_number=1, regions=[Region(id="r1", type="TEXT", content="test")])])
    assert len(tree["pages"]) == 1
    assert tree["pages"][0]["regions"][0]["content"] == "test"

def test_pipeline_state_required_only():
    state = PipelineState(document_id="doc1", job_id="job1")
    assert state["document_id"] == "doc1"

def test_pipeline_state_flexible_extension():
    state = PipelineState(document_id="doc1", job_id="job1", metadata={"new_field": "works"})
    assert state["metadata"]["new_field"] == "works"

def test_document_profile():
    profile = DocumentProfile(doc_type="invoice", confidence=0.94)
    assert profile["doc_type"] == "invoice"

def test_ontology_node():
    node = OntologyNode(name="total", field_type="CURRENCY", description="Total amount due")
    assert node["name"] == "total"

def test_extraction_schema():
    schema = ExtractionSchema(schema_id="inv_v1", doc_type="invoice", version="1.0", nodes=[OntologyNode(name="total", field_type="CURRENCY")])
    assert len(schema["nodes"]) == 1

def test_quality_report():
    report = ParseQualityReport(document_id="doc1", overall_score=0.87)
    assert report["overall_score"] == 0.87

def test_model_registry_register_and_get():
    reg = ModelRegistry()
    reg.register("DocumentProfile", {"type": "object", "fields": ["doc_type"]}, "1.0")
    schema = reg.get_schema("DocumentProfile")
    assert schema["fields"] == ["doc_type"]

def test_model_registry_versioning():
    reg = ModelRegistry()
    reg.register("DocumentProfile", {"fields": ["doc_type"]}, "1.0")
    reg.register("DocumentProfile", {"fields": ["doc_type", "complexity"]}, "2.0")
    v1 = reg.get_schema("DocumentProfile", "1.0")
    v2 = reg.get_schema("DocumentProfile", "2.0")
    latest = reg.get_schema("DocumentProfile")
    assert len(v1["fields"]) == 1
    assert len(v2["fields"]) == 2
    assert latest == v2
