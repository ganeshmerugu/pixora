"""Smart field extraction — uses any available LLM to understand document structure.

No hardcoded rules. The LLM figures out what's a label vs value, handles
multi-line layouts, mixed languages, and any document type generically.

Provider priority: Gemini (free) → Groq (cheap) → Together → Claude
"""
from __future__ import annotations
import logging
from typing import Any
from pixora.ocr.json_utils import extract_json_object

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a document data extraction system. Extract ALL structured fields from this document text.

Rules:
1. Identify every label-value pair, even if the label and value are on separate lines
2. Use the LABEL as the JSON key (snake_case), and the actual VALUE as the JSON value
3. Names of people, places, companies are VALUES — never use them as keys
4. Ignore decorative text, headers that aren't data fields, stamps, signatures
5. For dates, extract only the date — not surrounding words like "Signature"
6. Numbers that appear standalone (like barcodes, serial numbers) — include them with a descriptive key
7. If text is in multiple languages, use the English label as the key
8. Skip garbage/unreadable OCR artifacts

Document text:
{text}

Return ONLY a JSON object. Example format:
{{"name": "John Doe", "date_of_birth": "01/15/1990", "document_number": "ABC123"}}"""

VISION_EXTRACTION_PROMPT = """Extract ALL structured data from this document image.

Return a JSON object where:
- Keys are descriptive field names in snake_case (use the field LABEL, not the value)
- Values are the exact text shown in the document
- Names of people are VALUES, not keys
- Dates should contain only the date, not extra words
- Include all visible fields: IDs, names, dates, numbers, addresses

Return ONLY valid JSON. No explanation."""


async def smart_extract(
    text: str = "",
    image_bytes: bytes = b"",
    doc_type: str = "",
) -> tuple[dict[str, Any], str]:
    provider, provider_name = _get_best_provider()

    if not provider:
        return {}, "none"

    if image_bytes and hasattr(provider, "analyze_image"):
        try:
            resp = await provider.analyze_image(image_bytes, VISION_EXTRACTION_PROMPT)
            content = resp.get("content", "")
            parsed = extract_json_object(content)
            if parsed and any(k for k in parsed if not k.startswith("_")):
                logger.info("smart_extractor: VLM extraction via %s — %d fields", provider_name, len(parsed))
                return parsed, f"vlm_{provider_name}"
        except Exception as exc:
            logger.warning("smart_extractor: VLM failed (%s): %s", provider_name, exc)

    if text and hasattr(provider, "generate"):
        try:
            prompt = EXTRACTION_PROMPT.format(text=text[:8000])
            resp = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            content = resp.get("content", "")
            parsed = extract_json_object(content)
            if parsed and any(k for k in parsed if not k.startswith("_")):
                logger.info("smart_extractor: LLM extraction via %s — %d fields", provider_name, len(parsed))
                return parsed, f"llm_{provider_name}"
        except Exception as exc:
            logger.warning("smart_extractor: LLM failed (%s): %s", provider_name, exc)

    return {}, "none"


def _get_best_provider():
    try:
        from pixora.config.settings import settings

        if settings.gemini_api_key:
            from pixora.providers.gemini_provider import GeminiProvider
            return GeminiProvider(api_key=settings.gemini_api_key), "gemini"

        if settings.groq_api_key:
            from pixora.providers.groq_provider import GroqProvider
            return GroqProvider(api_key=settings.groq_api_key), "groq"

        if settings.together_api_key:
            from pixora.providers.together_ai import TogetherAIProvider
            return TogetherAIProvider(api_key=settings.together_api_key), "together"

        if settings.anthropic_api_key:
            from pixora.providers.claude import ClaudeProvider
            return ClaudeProvider(api_key=settings.anthropic_api_key), "claude"

    except Exception as exc:
        logger.debug("smart_extractor: no provider available: %s", exc)

    return None, "none"
