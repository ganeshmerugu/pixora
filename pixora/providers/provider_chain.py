"""Single provider chain — one place to resolve VLM/LLM providers.

Replaces 3 duplicate chain builders in vlm_harness, smart_pipeline, smart_extractor.
"""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)

_cached_chain: list[tuple[Any, str]] | None = None


def get_vlm_chain() -> list[tuple[Any, str]]:
    """Returns ordered list of (provider, name) for VLM/LLM tasks."""
    global _cached_chain
    if _cached_chain is not None:
        return _cached_chain

    chain: list[tuple[Any, str]] = []
    try:
        from pixora.config.settings import settings

        if settings.gemini_api_key:
            from pixora.providers.gemini_provider import GeminiProvider
            chain.append((GeminiProvider(api_key=settings.gemini_api_key), "gemini"))

        if settings.groq_api_key:
            from pixora.providers.groq_provider import GroqProvider
            chain.append((GroqProvider(api_key=settings.groq_api_key, model="llama-3.2-90b-vision-preview"), "groq_vision"))

        if settings.replicate_api_token:
            from pixora.providers.replicate_provider import ReplicateProvider
            chain.append((ReplicateProvider(api_token=settings.replicate_api_token), "replicate"))

        if settings.anthropic_api_key:
            from pixora.providers.claude import ClaudeProvider
            chain.append((ClaudeProvider(api_key=settings.anthropic_api_key), "claude"))

    except Exception as exc:
        logger.debug("provider_chain: build error: %s", exc)

    _cached_chain = chain
    return chain


def get_best_provider() -> tuple[Any, str] | tuple[None, str]:
    chain = get_vlm_chain()
    if chain:
        return chain[0]
    return None, "none"


def has_vlm() -> bool:
    return len(get_vlm_chain()) > 0


def reset_cache():
    global _cached_chain
    _cached_chain = None
