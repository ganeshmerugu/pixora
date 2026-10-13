from __future__ import annotations
import pytest
from docforge.providers.base import LLMProvider, VisionProvider, ClassificationProvider, LLMResponse, VisionResponse, ClassificationResult
from docforge.providers.registry import ProviderRegistry


def test_registry_register_and_get():
    registry = ProviderRegistry()
    class FakeLLM:
        provider_name = "fake"
        async def generate(self, messages, system="", max_tokens=4096, temperature=0.0, response_format=None):
            return LLMResponse(content="hello", tokens_used=10, cost_usd=0.0, model="fake", latency_ms=1)
        def estimate_tokens(self, text):
            return len(text) // 4
    registry.register("llm", FakeLLM())
    provider = registry.get("llm")
    assert provider.provider_name == "fake"


def test_registry_get_missing_raises():
    registry = ProviderRegistry()
    with pytest.raises(KeyError):
        registry.get("llm")


def test_registry_swap():
    registry = ProviderRegistry()
    class ProviderA:
        provider_name = "a"
    class ProviderB:
        provider_name = "b"
    registry.register("llm", ProviderA())
    assert registry.get("llm").provider_name == "a"
    registry.swap("llm", ProviderB())
    assert registry.get("llm").provider_name == "b"


def test_registry_list_providers():
    registry = ProviderRegistry()
    class FakeLLM:
        provider_name = "claude"
    class FakeVision:
        provider_name = "claude"
    registry.register("llm", FakeLLM())
    registry.register("vision", FakeVision())
    result = registry.list_providers()
    assert result == {"llm": "claude", "vision": "claude"}


def test_llm_response_required_fields():
    resp = LLMResponse(content="test")
    assert resp["content"] == "test"


def test_vision_response_required_fields():
    resp = VisionResponse(content="test")
    assert resp["content"] == "test"


def test_classification_result_required_fields():
    resp = ClassificationResult(doc_type="invoice", confidence=0.95)
    assert resp["doc_type"] == "invoice"
    assert resp["confidence"] == 0.95
