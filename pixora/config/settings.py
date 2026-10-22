from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import Any


class Settings(BaseSettings):
    model_config = {"env_prefix": "PIXORA_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    api_key: str = ""
    log_level: str = "INFO"

    # Database (SQLite for dev, PostgreSQL for prod)
    database_url: str = "sqlite+aiosqlite:///pixora.db"
    redis_url: str = ""

    provider_config: dict[str, dict[str, Any]] = {
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vision": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "embedding": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "classification": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "ocr_primary": {"provider": "tesseract"},
        "ocr_secondary": {"provider": "claude", "model": "claude-sonnet-4-6"},
    }

    # Model Hub
    default_tier: int = 1
    max_tier: int = 3
    quality_threshold: float = 0.80
    max_cost_per_doc: float = 0.10
    enable_tier_escalation: bool = True

    # AI Provider keys
    typesafe_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    together_api_key: str = ""
    replicate_api_token: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    tls_verify: str = "true"
    deployment_mode: str = "serverless"
    budget_limit_usd: float = 1.0

    # Auth
    jwt_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Local models
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    hf_cache_dir: str = ""
    hf_default_vlm: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    gpu_enabled: bool = False
    gpu_memory_gb: float = 0.0
    quantization: str = "4bit"
    ocr_engines: list[str] = ["tesseract", "easyocr"]
    ocr_ensemble_enabled: bool = True

    # Stripe payments
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@pixora.ai"

    # File storage (S3-compatible: AWS S3, Cloudflare R2, MinIO)
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint: str = ""

    # Monitoring
    sentry_dsn: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_parse_per_minute: int = 20


settings = Settings()
