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


@runtime_checkable
class ClassificationProvider(Protocol):
    provider_name: str
    async def classify(self, content: str | bytes, categories: list[dict[str, str]]) -> ClassificationResult: ...
