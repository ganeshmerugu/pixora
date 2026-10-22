"""Vertex AI provider — Gemini and open-source models via GCP Model Garden.

Uses Application Default Credentials (ADC) — no API keys needed.
On Cloud Run, the service account authenticates automatically.

Pricing (Gemini 2.0 Flash):
  - Input:  $0.10 / 1M tokens (text), $0.10 / 1M tokens (image)
  - Output: $0.40 / 1M tokens
  - ~$0.0003 per document page

Open-source models from Model Garden (e.g., PaliGemma, Qwen2-VL) can be
deployed to Vertex AI endpoints and used via the same interface.
"""
from __future__ import annotations
import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_API_BASE = "https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}"

DEFAULT_MODEL = "gemini-2.0-flash-001"
DEFAULT_REGION = "us-central1"

INPUT_COST_PER_1M = 0.10
OUTPUT_COST_PER_1M = 0.40


class VertexAIProvider:
    """Vertex AI Gemini provider using Application Default Credentials."""

    provider_name = "vertex_ai"

    def __init__(
        self,
        project_id: str = "",
        region: str = DEFAULT_REGION,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ):
        self._project = project_id
        self._region = region
        self._model = model
        self._timeout = timeout
        self._total_cost = 0.0
        self._total_requests = 0
        self._credentials = None
        self._http_client = None

    async def _get_client(self):
        if self._http_client is not None:
            return self._http_client

        import httpx
        import google.auth
        import google.auth.transport.requests
        import os

        if not self._project:
            creds, project = google.auth.default()
            self._project = self._project or project or os.environ.get("GCLOUD_PROJECT", "")
            self._credentials = creds
        else:
            self._credentials, _ = google.auth.default()

        self._credentials.refresh(google.auth.transport.requests.Request())

        verify = os.environ.get("PIXORA_TLS_VERIFY", "true").lower() not in ("0", "false", "no")
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            verify=verify,
        )
        return self._http_client

    def _get_headers(self) -> dict[str, str]:
        import google.auth.transport.requests
        if self._credentials.expired:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return {
            "Authorization": f"Bearer {self._credentials.token}",
            "Content-Type": "application/json",
        }

    def _build_url(self, action: str = "generateContent") -> str:
        return (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{self._project}/locations/{self._region}/"
            f"publishers/google/models/{self._model}:{action}"
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return round(
            (input_tokens / 1_000_000) * INPUT_COST_PER_1M
            + (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M,
            6,
        )

    async def generate(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()
        client = await self._get_client()

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        for msg in messages:
            role = "user" if msg.get("role") != "assistant" else "model"
            content = msg.get("content", "")
            if isinstance(content, str):
                contents.append({"role": role, "parts": [{"text": content}]})
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append({"text": block["text"]})
                        elif block.get("type") == "image_url":
                            url = block["image_url"]["url"]
                            if url.startswith("data:"):
                                mime, b64 = url.split(";base64,", 1)
                                mime = mime.replace("data:", "")
                                parts.append({"inlineData": {"mimeType": mime, "data": b64}})
                contents.append({"role": role, "parts": parts})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        resp = await client.post(
            self._build_url("generateContent"),
            headers=self._get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        cost = self._estimate_cost(input_tokens, output_tokens)
        self._total_cost += cost
        self._total_requests += 1

        return {
            "content": text,
            "tokens_used": input_tokens + output_tokens,
            "cost_usd": cost,
            "model": self._model,
            "latency_ms": int((time.monotonic() - start) * 1000),
        }

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()
        client = await self._get_client()

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

        resp = await client.post(
            self._build_url("generateContent"),
            headers=self._get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        cost = self._estimate_cost(input_tokens, output_tokens)
        self._total_cost += cost
        self._total_requests += 1

        return {
            "content": text,
            "tokens_used": input_tokens + output_tokens,
            "cost_usd": cost,
            "model": self._model,
            "latency_ms": int((time.monotonic() - start) * 1000),
        }

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    async def is_available(self) -> bool:
        try:
            await self._get_client()
            return bool(self._project)
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "vertex_ai",
            "model": self._model,
            "project": self._project,
            "region": self._region,
            "total_cost_usd": round(self._total_cost, 6),
            "total_requests": self._total_requests,
        }

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
