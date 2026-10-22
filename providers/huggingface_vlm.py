from __future__ import annotations
import asyncio
import base64
import io
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class HuggingFaceVLMProvider:
    """Provider for HuggingFace vision-language models (Qwen2.5-VL, Florence-2, GOT-OCR2).

    Loads model lazily on first use. Supports 4-bit quantization for GPU-constrained environments.
    """

    provider_name = "huggingface_vlm"

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        device: str = "auto",
        quantization: str | None = "4bit",
        max_memory: dict[str, str] | None = None,
        torch_dtype: str = "float16",
    ):
        self._model_id = model_id
        self._device = device
        self._quantization = quantization
        self._max_memory = max_memory
        self._torch_dtype = torch_dtype
        self._model = None
        self._processor = None
        self._tokenizer = None
        self._total_tokens = 0
        self._total_requests = 0

    def _load_model(self) -> None:
        if self._model is not None:
            return

        logger.info("huggingface_vlm: loading model '%s'...", self._model_id)
        import torch
        from transformers import AutoProcessor, AutoModelForCausalLM, BitsAndBytesConfig

        dtype = getattr(torch, self._torch_dtype, torch.float16)
        kwargs: dict[str, Any] = {
            "torch_dtype": dtype,
            "device_map": self._device,
            "trust_remote_code": True,
        }
        if self._max_memory:
            kwargs["max_memory"] = self._max_memory

        if self._quantization == "4bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif self._quantization == "8bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)

        self._processor = AutoProcessor.from_pretrained(self._model_id, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(self._model_id, **kwargs)
        self._tokenizer = getattr(self._processor, "tokenizer", self._processor)

        logger.info("huggingface_vlm: model loaded successfully")

    async def generate(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.0,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._generate_sync, messages, system, max_tokens, temperature,
        )

    def _generate_sync(
        self,
        messages: list[dict[str, str]],
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        import torch
        self._load_model()
        start = time.monotonic()

        if system:
            messages = [{"role": "system", "content": system}] + messages

        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        gen_kwargs: dict[str, Any] = {"max_new_tokens": max_tokens}
        if temperature > 0:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["do_sample"] = True
        else:
            gen_kwargs["do_sample"] = False

        with torch.no_grad():
            outputs = self._model.generate(**inputs, **gen_kwargs)

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        content = self._tokenizer.decode(new_tokens, skip_special_tokens=True)

        total_tokens = outputs.shape[1]
        latency_ms = int((time.monotonic() - start) * 1000)
        self._total_tokens += total_tokens
        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": 0.0,
            "model": self._model_id,
            "latency_ms": latency_ms,
        }

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._analyze_image_sync, image_bytes, prompt, max_tokens,
        )

    def _analyze_image_sync(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        import torch
        from PIL import Image
        self._load_model()
        start = time.monotonic()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._processor(text=text, images=[image], return_tensors="pt").to(self._model.device)

        with torch.no_grad():
            outputs = self._model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        content = self._processor.decode(new_tokens, skip_special_tokens=True)

        total_tokens = outputs.shape[1]
        latency_ms = int((time.monotonic() - start) * 1000)
        self._total_tokens += total_tokens
        self._total_requests += 1

        return {
            "content": content,
            "tokens_used": total_tokens,
            "cost_usd": 0.0,
            "model": self._model_id,
            "latency_ms": latency_ms,
        }

    def estimate_tokens(self, text: str) -> int:
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return len(text) // 4

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": "huggingface_vlm",
            "model": self._model_id,
            "total_tokens": self._total_tokens,
            "total_requests": self._total_requests,
            "total_cost_usd": 0.0,
            "loaded": self._model is not None,
        }
