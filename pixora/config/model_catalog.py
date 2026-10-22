from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict


class ModelSpec(TypedDict, total=False):
    model_id: Required[str]
    name: Required[str]
    provider_type: Required[str]
    capabilities: Required[list[str]]
    tier: Required[int]
    cost_per_1k_tokens: float
    cost_per_image: float
    min_gpu_gb: float
    quantization: str
    context_window: int
    supports_vision: bool
    supports_structured_output: bool
    model_source: str
    hf_model_id: str
    ollama_model: str
    description: str
    metadata: dict[str, Any]


TIER_NAMES = {1: "free", 2: "cheap", 3: "enterprise"}


MODEL_CATALOG: list[ModelSpec] = [
    # ── Tier 1: FREE (CPU, no API cost) ──────────────────────────
    ModelSpec(
        model_id="tesseract-5",
        name="Tesseract 5",
        provider_type="ocr_engine",
        capabilities=["ocr"],
        tier=1,
        cost_per_1k_tokens=0.0,
        cost_per_image=0.0,
        min_gpu_gb=0,
        context_window=0,
        supports_vision=False,
        model_source="system",
        description="Industry-standard open-source OCR. Best for clean printed text.",
    ),
    ModelSpec(
        model_id="easyocr",
        name="EasyOCR",
        provider_type="ocr_engine",
        capabilities=["ocr"],
        tier=1,
        cost_per_1k_tokens=0.0,
        cost_per_image=0.0,
        min_gpu_gb=0,
        context_window=0,
        supports_vision=False,
        model_source="pip",
        description="Multilingual OCR with 80+ language support.",
    ),
    ModelSpec(
        model_id="rules-classifier",
        name="Rule-Based Classifier",
        provider_type="classifier",
        capabilities=["classification"],
        tier=1,
        cost_per_1k_tokens=0.0,
        min_gpu_gb=0,
        model_source="builtin",
        description="Regex pattern matching for document classification.",
    ),
    ModelSpec(
        model_id="basic-extractor",
        name="Basic Heuristic Extractor",
        provider_type="extractor",
        capabilities=["extraction"],
        tier=1,
        cost_per_1k_tokens=0.0,
        min_gpu_gb=0,
        model_source="builtin",
        description="Label:value pattern matching for field extraction.",
    ),

    # ── Tier 2: CHEAP (GPU, ~$0.001-0.005/doc) ──────────────────
    ModelSpec(
        model_id="surya-ocr",
        name="Surya OCR",
        provider_type="ocr_engine",
        capabilities=["ocr", "line_detection", "layout"],
        tier=2,
        cost_per_image=0.001,
        min_gpu_gb=4,
        model_source="huggingface",
        hf_model_id="vikp/surya_rec",
        description="State-of-the-art open-source OCR. Beats Tesseract on most benchmarks.",
    ),
    ModelSpec(
        model_id="doctr-ocr",
        name="docTR",
        provider_type="ocr_engine",
        capabilities=["ocr", "line_detection"],
        tier=2,
        cost_per_image=0.001,
        min_gpu_gb=4,
        model_source="huggingface",
        hf_model_id="mindee/doctr",
        description="Document OCR by Mindee. Pre-trained on document images.",
    ),
    ModelSpec(
        model_id="got-ocr2",
        name="GOT-OCR2",
        provider_type="vlm_ocr",
        capabilities=["ocr", "vision", "structured_extraction"],
        tier=2,
        cost_per_image=0.003,
        min_gpu_gb=8,
        model_source="huggingface",
        hf_model_id="stepfun-ai/GOT-OCR-2.0-hf",
        supports_vision=True,
        description="General OCR Theory model. Handles tables, math, formatted text.",
    ),
    ModelSpec(
        model_id="qwen25-vl-7b",
        name="Qwen2.5-VL-7B",
        provider_type="vlm",
        capabilities=["vision", "extraction", "classification", "ocr"],
        tier=2,
        cost_per_1k_tokens=0.0,
        cost_per_image=0.005,
        min_gpu_gb=8,
        quantization="4bit",
        context_window=32768,
        supports_vision=True,
        supports_structured_output=True,
        model_source="huggingface",
        hf_model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        description="Best open-source VLM. Document understanding, extraction, classification.",
    ),
    ModelSpec(
        model_id="florence-2",
        name="Florence-2-large",
        provider_type="vlm",
        capabilities=["vision", "ocr", "classification"],
        tier=2,
        cost_per_image=0.002,
        min_gpu_gb=4,
        supports_vision=True,
        model_source="huggingface",
        hf_model_id="microsoft/Florence-2-large",
        description="Microsoft lightweight VLM. Fast, good for structured extraction.",
    ),
    ModelSpec(
        model_id="qwen25-7b",
        name="Qwen2.5-7B-Instruct",
        provider_type="llm",
        capabilities=["extraction", "classification"],
        tier=2,
        cost_per_1k_tokens=0.0,
        min_gpu_gb=8,
        quantization="4bit",
        context_window=32768,
        supports_structured_output=True,
        model_source="ollama",
        ollama_model="qwen2.5:7b",
        description="Strong open-source LLM for text extraction and classification.",
    ),
    ModelSpec(
        model_id="llama31-8b",
        name="Llama-3.1-8B-Instruct",
        provider_type="llm",
        capabilities=["extraction", "classification"],
        tier=2,
        cost_per_1k_tokens=0.0,
        min_gpu_gb=8,
        quantization="4bit",
        context_window=131072,
        supports_structured_output=True,
        model_source="ollama",
        ollama_model="llama3.1:8b",
        description="Meta's flagship open-source LLM. Long context window.",
    ),
    ModelSpec(
        model_id="mistral-7b",
        name="Mistral-7B-Instruct",
        provider_type="llm",
        capabilities=["extraction"],
        tier=2,
        cost_per_1k_tokens=0.0,
        min_gpu_gb=6,
        quantization="4bit",
        context_window=32768,
        model_source="ollama",
        ollama_model="mistral:7b",
        description="Fast and efficient open-source LLM.",
    ),

    # ── Tier 1.5: SERVERLESS (API, ~$0.0001-0.003/doc) ────────────
    ModelSpec(
        model_id="groq-llama33-70b",
        name="Groq Llama-3.3-70B",
        provider_type="serverless_api",
        capabilities=["extraction", "classification"],
        tier=1,
        cost_per_1k_tokens=0.00059,
        min_gpu_gb=0,
        context_window=131072,
        supports_structured_output=True,
        model_source="api",
        description="Fastest LLM inference. ~300 tok/s. Cheapest option for extraction.",
    ),
    ModelSpec(
        model_id="groq-llama31-8b",
        name="Groq Llama-3.1-8B",
        provider_type="serverless_api",
        capabilities=["extraction", "classification"],
        tier=1,
        cost_per_1k_tokens=0.00005,
        min_gpu_gb=0,
        context_window=131072,
        supports_structured_output=True,
        model_source="api",
        description="Ultra-cheap small model for simple extractions.",
    ),
    ModelSpec(
        model_id="together-llama33-70b",
        name="Together Llama-3.3-70B",
        provider_type="serverless_api",
        capabilities=["extraction", "classification"],
        tier=1,
        cost_per_1k_tokens=0.00088,
        min_gpu_gb=0,
        context_window=131072,
        supports_structured_output=True,
        model_source="api",
        description="High-quality open-source LLM. Good fallback if Groq is down.",
    ),
    ModelSpec(
        model_id="together-qwen25-72b",
        name="Together Qwen2.5-72B",
        provider_type="serverless_api",
        capabilities=["extraction", "classification"],
        tier=1,
        cost_per_1k_tokens=0.0012,
        min_gpu_gb=0,
        context_window=32768,
        supports_structured_output=True,
        model_source="api",
        description="Best open-source model for structured extraction.",
    ),
    ModelSpec(
        model_id="replicate-qwen-vl",
        name="Replicate Qwen2.5-VL",
        provider_type="serverless_api",
        capabilities=["vision", "ocr", "extraction"],
        tier=2,
        cost_per_image=0.003,
        min_gpu_gb=0,
        supports_vision=True,
        model_source="api",
        description="Serverless VLM. Pay per image. Good for scanned documents.",
    ),

    # ── Tier 3: ENTERPRISE (API, ~$0.01-0.05/doc) ────────────────
    ModelSpec(
        model_id="claude-sonnet",
        name="Claude Sonnet 4.6",
        provider_type="api",
        capabilities=["extraction", "classification", "vision", "ocr"],
        tier=3,
        cost_per_1k_tokens=0.003,
        cost_per_image=0.005,
        min_gpu_gb=0,
        context_window=200000,
        supports_vision=True,
        supports_structured_output=True,
        model_source="api",
        description="Anthropic's Claude. Best quality for document understanding.",
    ),
    ModelSpec(
        model_id="gpt4-vision",
        name="GPT-4 Vision",
        provider_type="api",
        capabilities=["extraction", "classification", "vision", "ocr"],
        tier=3,
        cost_per_1k_tokens=0.01,
        cost_per_image=0.01,
        min_gpu_gb=0,
        context_window=128000,
        supports_vision=True,
        supports_structured_output=True,
        model_source="api",
        description="OpenAI GPT-4 with vision. Strong document extraction.",
    ),
]


def get_models_by_tier(tier: int) -> list[ModelSpec]:
    return [m for m in MODEL_CATALOG if m["tier"] == tier]


def get_models_by_capability(capability: str) -> list[ModelSpec]:
    return [m for m in MODEL_CATALOG if capability in m["capabilities"]]


def get_model(model_id: str) -> ModelSpec | None:
    for m in MODEL_CATALOG:
        if m["model_id"] == model_id:
            return m
    return None


def get_cheapest_model(capability: str, max_tier: int = 3) -> ModelSpec | None:
    candidates = [
        m for m in MODEL_CATALOG
        if capability in m["capabilities"] and m["tier"] <= max_tier
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda m: (m["tier"], m.get("cost_per_image", 0) + m.get("cost_per_1k_tokens", 0)))
