from __future__ import annotations
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_PRICING: dict[str, tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "mixtral-8x7b-32768": (0.24, 0.24),
    "gemma2-9b-it": (0.20, 0.20),
}


class GroqProvider:
    provider_name = "groq"

    def __init__(
        self,
        api_key: str = "",
        model: str = "llama-3.3-70b-versatile",
        timeout: float = 30.0,
    ):
        if not HAS_HTTPX:
            raise ImportError("httpx required: pip install httpx")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self._total_cost = 0.0
        self._total_tokens = 0
        self._total_requests = 0

    async def generate(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()

        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        resp = await self._client.post(
            GROQ_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        pricing = GROQ_PRICING.get(self._model, (0.59, 0.79))
        cost = (prompt_tokens * pricing[0] + completion_tokens * pricing[1]) / 1_000_000
        latency_ms = int((time.monotonic() - start) * 1000)

        self._total_cost += cost
        self._total_tokens += total_tokens
        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": round(cost, 6),
            "model": self._model,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    async def is_available(self) -> bool:
        return bool(self._api_key)

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "groq",
            "model": self._model,
            "total_cost_usd": round(self._total_cost, 6),
            "total_tokens": self._total_tokens,
            "total_requests": self._total_requests,
        }

    async def close(self) -> None:
        await self._client.aclose()
