from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import Any


class Settings(BaseSettings):
    model_config = {"env_prefix": "PIXORA_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pixora"
    redis_url: str = "redis://localhost:6379/0"
    tesseract_path: str = "tesseract"
    log_level: str = "INFO"
    otel_exporter_endpoint: str = ""

    provider_config: dict[str, dict[str, Any]] = {
        "llm": {"provider": "vertex_ai", "model": "gemini-2.0-flash-001"},
        "vision": {"provider": "vertex_ai", "model": "gemini-2.0-flash-001"},
        "embedding": {"provider": "none"},
        "classification": {"provider": "rule_based"},
        "ocr_primary": {"provider": "tesseract"},
        "ocr_secondary": {"provider": "easyocr"},
    }

    # Model Hub — capped at tier 2 (no frontier models)
    default_tier: int = 1
    max_tier: int = 2
    quality_threshold: float = 0.80
    max_cost_per_doc: float = 0.01
    enable_tier_escalation: bool = True

    # Serverless API keys (optional — Vertex AI uses IAM auth instead)
    gemini_api_key: str = ""
    groq_api_key: str = ""
    together_api_key: str = ""
    replicate_api_token: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    typesafe_api_key: str = ""
    tls_verify: str = "true"
    deployment_mode: str = "serverless"
    budget_limit_usd: float = 1.0

    # Local model infrastructure (optional, for self-hosted)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    hf_cache_dir: str = ""
    hf_default_vlm: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    gpu_enabled: bool = False
    gpu_memory_gb: float = 0.0
    quantization: str = "4bit"

    # OCR engine preferences
    ocr_engines: list[str] = ["tesseract", "easyocr"]
    ocr_ensemble_enabled: bool = True


settings = Settings()
