from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import Any


class Settings(BaseSettings):
    model_config = {"env_prefix": "DOCFORGE_"}

    api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docforge"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    tesseract_path: str = "tesseract"
    log_level: str = "INFO"
    otel_exporter_endpoint: str = ""

    provider_config: dict[str, dict[str, Any]] = {
        "llm": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "vision": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "embedding": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "classification": {"provider": "claude", "model": "claude-sonnet-4-6"},
        "ocr_primary": {"provider": "tesseract"},
        "ocr_secondary": {"provider": "claude", "model": "claude-sonnet-4-6"},
    }


settings = Settings()
