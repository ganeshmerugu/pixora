from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from typing_extensions import Required, TypedDict


class LLMResponse(TypedDict, total=False):
    content: Required[str]
    tokens_used: int
    cost_usd: float
    model: str
    latency_ms: int
    metadata: dict[str, Any]


class VisionResponse(TypedDict, total=False):
    content: Required[str]
    tokens_used: int
    cost_usd: float
    model: str
    latency_ms: int
    metadata: dict[str, Any]


class ClassificationResult(TypedDict, total=False):
    doc_type: Required[str]
    confidence: Required[float]
    reasoning: str
    model: str
    metadata: dict[str, Any]


class EmbeddingResult(TypedDict, total=False):
    embeddings: Required[list[list[float]]]
    model: str
    tokens_used: int
    metadata: dict[str, Any]


@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str
    async def generate(self, messages: list[dict], system: str = "", max_tokens: int = 4096, temperature: float = 0.0, response_format: dict | None = None) -> LLMResponse: ...
    def estimate_tokens(self, text: str) -> int: ...


@runtime_checkable
class VisionProvider(Protocol):
    provider_name: str
    async def analyze_image(self, image: bytes, prompt: str, max_tokens: int = 4096, response_format: dict | None = None) -> VisionResponse: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider_name: str
    async def embed(self, texts: list[str]) -> EmbeddingResult: ...


class ProviderCostProfile(TypedDict, total=False):
    provider_name: Required[str]
    cost_per_1k_input: Required[float]
    cost_per_1k_output: Required[float]
    estimated_quality: Required[float]
    is_free: bool
    rate_limit_rpm: int
    supports_vision: bool
    supports_text: bool


PROVIDER_COSTS: dict[str, ProviderCostProfile] = {
    "regex": ProviderCostProfile(provider_name="regex", cost_per_1k_input=0.0, cost_per_1k_output=0.0, estimated_quality=0.55, is_free=True, supports_vision=False, supports_text=True),
    "tesseract": ProviderCostProfile(provider_name="tesseract", cost_per_1k_input=0.0, cost_per_1k_output=0.0, estimated_quality=0.60, is_free=True, supports_vision=True, supports_text=False),
    "gemini": ProviderCostProfile(provider_name="gemini", cost_per_1k_input=0.0, cost_per_1k_output=0.0, estimated_quality=0.82, is_free=True, rate_limit_rpm=15, supports_vision=True, supports_text=True),
    "groq": ProviderCostProfile(provider_name="groq", cost_per_1k_input=0.0002, cost_per_1k_output=0.0002, estimated_quality=0.78, supports_vision=True, supports_text=True),
    "together": ProviderCostProfile(provider_name="together", cost_per_1k_input=0.0003, cost_per_1k_output=0.0003, estimated_quality=0.76, supports_vision=True, supports_text=True),
    "vertex_ai": ProviderCostProfile(provider_name="vertex_ai", cost_per_1k_input=0.0, cost_per_1k_output=0.0, estimated_quality=0.85, is_free=True, supports_vision=True, supports_text=True),
    "claude": ProviderCostProfile(provider_name="claude", cost_per_1k_input=0.003, cost_per_1k_output=0.015, estimated_quality=0.92, supports_vision=True, supports_text=True),
}


@runtime_checkable
class ClassificationProvider(Protocol):
    provider_name: str
    async def classify(self, content: str | bytes, categories: list[dict[str, str]]) -> ClassificationResult: ...
