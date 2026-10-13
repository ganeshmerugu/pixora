from __future__ import annotations
import time
from typing import Any
import anthropic
from docforge.providers.base import LLMResponse, VisionResponse, ClassificationResult, EmbeddingResult


class ClaudeProvider:
    provider_name = "claude"

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: dict | None = None,
    ) -> LLMResponse:
        start = time.monotonic()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if temperature != 0.0:
            kwargs["temperature"] = temperature

        response = await self._client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - start) * 1000)
        content = response.content[0].text if response.content else ""
        tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
        cost_usd = _estimate_cost(self._model, response.usage.input_tokens or 0, response.usage.output_tokens or 0)
        return LLMResponse(
            content=content,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            model=self._model,
            latency_ms=latency_ms,
        )

    async def analyze_image(
        self,
        image: bytes,
        prompt: str,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> VisionResponse:
        import base64
        start = time.monotonic()
        image_b64 = base64.standard_b64encode(image).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        content = response.content[0].text if response.content else ""
        tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
        cost_usd = _estimate_cost(self._model, response.usage.input_tokens or 0, response.usage.output_tokens or 0)
        return VisionResponse(
            content=content,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            model=self._model,
            latency_ms=latency_ms,
        )

    async def classify(
        self,
        content: str | bytes,
        categories: list[dict[str, str]],
    ) -> ClassificationResult:
        import json
        if isinstance(content, bytes):
            text_content = content.decode("utf-8", errors="replace")
        else:
            text_content = content
        categories_str = "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in categories)
        prompt = (
            f"Classify the following document into one of these categories:\n{categories_str}\n\n"
            f"Document:\n{text_content[:4000]}\n\n"
            "Respond with JSON: {\"doc_type\": \"<category_name>\", \"confidence\": <0.0-1.0>, \"reasoning\": \"<brief reason>\"}"
        )
        response = await self.generate(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        try:
            parsed = json.loads(response["content"])
            return ClassificationResult(
                doc_type=parsed["doc_type"],
                confidence=float(parsed["confidence"]),
                reasoning=parsed.get("reasoning", ""),
                model=self._model,
            )
        except (json.JSONDecodeError, KeyError):
            return ClassificationResult(
                doc_type=categories[0]["name"] if categories else "unknown",
                confidence=0.0,
                reasoning="Failed to parse classification response",
                model=self._model,
            )

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        # Claude does not natively support embeddings; raise to signal use a dedicated embedding provider
        raise NotImplementedError("ClaudeProvider does not support embeddings. Use a dedicated embedding provider.")

    def estimate_tokens(self, text: str) -> int:
        # Rough approximation: ~4 characters per token
        return max(1, len(text) // 4)


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    # Pricing as of 2024 in USD per million tokens (approximate)
    pricing: dict[str, tuple[float, float]] = {
        "claude-3-5-sonnet-20241022": (3.0, 15.0),
        "claude-3-5-haiku-20241022": (0.8, 4.0),
        "claude-3-opus-20240229": (15.0, 75.0),
        "claude-3-sonnet-20240229": (3.0, 15.0),
        "claude-3-haiku-20240307": (0.25, 1.25),
    }
    input_price, output_price = pricing.get(model, (3.0, 15.0))
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
