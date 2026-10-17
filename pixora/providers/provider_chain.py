"""Single provider chain — one place to resolve VLM/LLM providers.

Two chains:
  - VLM chain: providers that can see images (Gemini, Replicate, Claude)
  - LLM chain: providers that process text only (Groq, Together, Claude)

Groq does NOT support vision — it's LLM-only for text extraction.
"""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)

_vlm_chain: list[tuple[Any, str]] | None = None
_llm_chain: list[tuple[Any, str]] | None = None


def get_vlm_chain() -> list[tuple[Any, str]]:
    """Providers that can analyze images (have analyze_image method)."""
    global _vlm_chain
    if _vlm_chain is not None:
        return _vlm_chain

    chain: list[tuple[Any, str]] = []
    try:
        from pixora.config.settings import settings

        if settings.gemini_api_key:
            from pixora.providers.gemini_provider import GeminiProvider
            chain.append((GeminiProvider(api_key=settings.gemini_api_key), "gemini"))

        if settings.replicate_api_token:
            from pixora.providers.replicate_provider import ReplicateProvider
            chain.append((ReplicateProvider(api_token=settings.replicate_api_token), "replicate"))

        if settings.anthropic_api_key:
            from pixora.providers.claude import ClaudeProvider
            chain.append((ClaudeProvider(api_key=settings.anthropic_api_key), "claude"))

    except Exception as exc:
        logger.debug("provider_chain: VLM build error: %s", exc)

    _vlm_chain = chain
    return chain


def get_llm_chain() -> list[tuple[Any, str]]:
    """Providers that can process text (have generate method). Includes VLM providers too."""
    global _llm_chain
    if _llm_chain is not None:
        return _llm_chain

    chain: list[tuple[Any, str]] = []
    try:
        from pixora.config.settings import settings

        if settings.gemini_api_key:
            from pixora.providers.gemini_provider import GeminiProvider
            chain.append((GeminiProvider(api_key=settings.gemini_api_key), "gemini"))

        if settings.groq_api_key:
            from pixora.providers.groq_provider import GroqProvider
            chain.append((GroqProvider(api_key=settings.groq_api_key, model="qwen/qwen3.8-27b"), "groq"))

        if settings.anthropic_api_key:
            from pixora.providers.claude import ClaudeProvider
            chain.append((ClaudeProvider(api_key=settings.anthropic_api_key), "claude"))

    except Exception as exc:
        logger.debug("provider_chain: LLM build error: %s", exc)

    _llm_chain = chain
    return chain


def get_best_provider() -> tuple[Any, str] | tuple[None, str]:
    """Best provider for text tasks (LLM chain, includes Groq)."""
    chain = get_llm_chain()
    if chain:
        return chain[0]
    return None, "none"


def get_best_vlm() -> tuple[Any, str] | tuple[None, str]:
    """Best provider for image tasks (VLM chain, no Groq)."""
    chain = get_vlm_chain()
    if chain:
        return chain[0]
    return None, "none"


def has_vlm() -> bool:
    return len(get_vlm_chain()) > 0


def has_llm() -> bool:
    return len(get_llm_chain()) > 0


def reset_cache():
    global _vlm_chain, _llm_chain
    _vlm_chain = None
    _llm_chain = None
