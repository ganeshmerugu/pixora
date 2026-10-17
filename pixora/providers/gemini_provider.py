"""Google Gemini provider — free tier VLM for document understanding.

Gemini 2.0 Flash: free 15 RPM, 1500 requests/day, excellent at documents.
Used as VLM escalation when OCR text quality is too low.
"""
from __future__ import annotations
import base64
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-flash-latest"


class GeminiProvider:
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ):
        if not HAS_HTTPX:
            raise ImportError("httpx required: pip install httpx")
        self._api_key = api_key
        self._model = model
        import ssl
        verify = os.environ.get("PIXORA_TLS_VERIFY", "true").lower() not in ("0", "false", "no")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout), verify=verify)
        self._total_cost = 0.0
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

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        for msg in messages:
            role = "user" if msg.get("role") != "assistant" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        model_id = self._model.replace("models/", "")
        url = f"{GEMINI_API_URL}/{model_id}:generateContent?key={self._api_key}"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        total_tokens = usage.get("totalTokenCount", 0)
        latency_ms = int((time.monotonic() - start) * 1000)

        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": 0.0,
            "model": self._model,
            "latency_ms": latency_ms,
        }

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        mime = "image/png"
        if image_bytes[:3] == b"\xff\xd8\xff":
            mime = "image/jpeg"
        elif image_bytes[:4] == b"RIFF":
            mime = "image/webp"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime, "data": b64_image}},
                    {"text": prompt},
                ],
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.0,
            },
        }

        model_id = self._model.replace("models/", "")
        url = f"{GEMINI_API_URL}/{model_id}:generateContent?key={self._api_key}"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        total_tokens = usage.get("totalTokenCount", 0)
        latency_ms = int((time.monotonic() - start) * 1000)

        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": 0.0,
            "model": self._model,
            "latency_ms": latency_ms,
        }

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    async def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            url = f"{GEMINI_API_URL}?key={self._api_key}"
            resp = await self._client.get(url)
            return resp.status_code == 200
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "gemini",
            "model": self._model,
            "total_cost_usd": 0.0,
            "total_requests": self._total_requests,
            "note": "Free tier: 15 RPM, 1500 req/day",
        }

    async def close(self) -> None:
        await self._client.aclose()
