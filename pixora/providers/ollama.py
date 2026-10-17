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


class OllamaProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout: float = 120.0,
    ):
        if not HAS_HTTPX:
            raise ImportError("httpx is required for OllamaProvider: pip install httpx")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
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

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + messages
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        resp = await self._client.post(f"{self._base_url}/api/chat", json=payload)
        resp.raise_for_status()
        result = resp.json()

        content = result.get("message", {}).get("content", "")
        prompt_tokens = result.get("prompt_eval_count", 0)
        completion_tokens = result.get("eval_count", 0)
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = int((time.monotonic() - start) * 1000)

        self._total_tokens += total_tokens
        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": 0.0,
            "model": self._model,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    async def is_available(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("ollama: failed to list models: %s", exc)
            return []

    async def pull_model(self, model: str) -> bool:
        try:
            resp = await self._client.post(
                f"{self._base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=httpx.Timeout(600.0),
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.error("ollama: failed to pull model '%s': %s", model, exc)
            return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "ollama",
            "model": self._model,
            "total_tokens": self._total_tokens,
            "total_requests": self._total_requests,
            "total_cost_usd": 0.0,
        }

    async def close(self) -> None:
        await self._client.aclose()
