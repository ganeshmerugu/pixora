from __future__ import annotations
import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"

REPLICATE_MODELS: dict[str, str] = {
    "qwen-vl": "lucataco/qwen2-vl-7b-instruct:615ba98fdf1511e2aa90b09c4e7716c872a0064a5c97e73ffcde218090325e5d",
    "llava": "yorickvp/llava-v1.6-34b:41ecfbfb261e6c1adf3ad896c9066ca98346996d7c4045c5bc944a79d430f174",
    "got-ocr": "stepfun-ai/got-ocr-2.0:3f9e7ddc2d4a6c04b50e9e58e0e4a4c3a72f1c3b",
}


class ReplicateProvider:
    provider_name = "replicate"

    def __init__(
        self,
        api_token: str = "",
        default_model: str = "qwen-vl",
        timeout: float = 120.0,
    ):
        if not HAS_HTTPX:
            raise ImportError("httpx required: pip install httpx")
        self._api_token = api_token
        self._default_model = default_model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self._total_cost = 0.0
        self._total_requests = 0

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        image_uri = f"data:image/png;base64,{b64_image}"

        model_version = REPLICATE_MODELS.get(self._default_model, REPLICATE_MODELS["qwen-vl"])

        payload = {
            "version": model_version,
            "input": {
                "image": image_uri,
                "prompt": prompt,
                "max_tokens": max_tokens,
            },
        }

        resp = await self._client.post(
            REPLICATE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        prediction = resp.json()

        prediction_url = prediction.get("urls", {}).get("get", "")
        if not prediction_url:
            prediction_url = f"{REPLICATE_API_URL}/{prediction['id']}"

        content = ""
        for _ in range(60):
            import asyncio
            await asyncio.sleep(2)

            poll_resp = await self._client.get(
                prediction_url,
                headers={"Authorization": f"Bearer {self._api_token}"},
            )
            poll_data = poll_resp.json()
            status = poll_data.get("status", "")

            if status == "succeeded":
                output = poll_data.get("output", "")
                if isinstance(output, list):
                    content = "".join(str(o) for o in output)
                else:
                    content = str(output)
                break
            elif status in ("failed", "canceled"):
                error = poll_data.get("error", "unknown error")
                logger.error("replicate: prediction failed: %s", error)
                break

        latency_ms = int((time.monotonic() - start) * 1000)
        cost = 0.003
        self._total_cost += cost
        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": 0,
            "cost_usd": round(cost, 6),
            "model": self._default_model,
            "latency_ms": latency_ms,
        }

    async def is_available(self) -> bool:
        return bool(self._api_token)

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "replicate",
            "model": self._default_model,
            "total_cost_usd": round(self._total_cost, 6),
            "total_requests": self._total_requests,
        }

    async def close(self) -> None:
        await self._client.aclose()
