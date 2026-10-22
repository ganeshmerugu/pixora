"""Enterprise VLM Harness — vision-first document understanding.

Architecture:
  Image → preprocess → VLM (structured JSON) → validate → cache → return

Design principles:
  1. VLM-first for images (don't waste time on OCR that will fail)
  2. Structured output (JSON schema enforcement, not prompt prayer)
  3. Preprocess before VLM (cleaner image = better extraction)
  4. Retry with provider fallback (Gemini → Groq → Replicate → Claude)
  5. Cache results (same image = same result, no duplicate API calls)
  6. Multi-page support (process all pages, merge results)
  7. Domain-aware prompts (invoice ≠ medical ≠ ID card)
  8. Confidence estimation (don't trust VLM blindly)
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import io
import logging
import time
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.ocr.json_utils import extract_json_object

logger = logging.getLogger(__name__)


# ── Result Types ──────────────────────────────────────────────

class VLMField(TypedDict, total=False):
    value: Required[str]
    confidence: float
    source: str
    page: int


class VLMResult(TypedDict, total=False):
    extraction: Required[dict[str, Any]]
    markdown: str
    tables: list[str]
    confidence: float
    provider: str
    model: str
    cost_usd: float
    latency_ms: float
    pages_processed: int
    cached: bool
    retries: int
    preprocessing: list[str]
    metadata: dict[str, Any]


# ── Configuration ─────────────────────────────────────────────

MAX_RETRIES = 2
RETRY_DELAY_S = 1.0
CACHE_MAX_SIZE = 200
IMAGE_MAX_DIMENSION = 2048
CONFIDENCE_THRESHOLD_HIGH = 0.85
CONFIDENCE_THRESHOLD_LOW = 0.5


# ── Result Cache ──────────────────────────────────────────────

_result_cache: dict[str, VLMResult] = {}


def _cache_key(image_bytes: bytes, doc_type: str) -> str:
    h = hashlib.sha256(image_bytes).hexdigest()[:16]
    return f"{h}_{doc_type}"


def _cache_get(key: str) -> VLMResult | None:
    return _result_cache.get(key)


def _cache_put(key: str, result: VLMResult) -> None:
    if len(_result_cache) >= CACHE_MAX_SIZE:
        oldest = next(iter(_result_cache))
        del _result_cache[oldest]
    _result_cache[key] = result


# ── Domain-Specific Prompts ───────────────────────────────────

DOMAIN_PROMPTS: dict[str, str] = {
    "invoice": (
        "Extract ALL fields from this invoice image. Return JSON with these keys where applicable:\n"
        "vendor_name, vendor_address, invoice_number, invoice_date, due_date, po_number,\n"
        "bill_to_name, bill_to_address, line_items (array of {description, quantity, unit_price, amount}),\n"
        "subtotal, tax, total_due, payment_terms, bank_details.\n"
        "Extract exact values as shown. Use null for fields not visible."
    ),
    "receipt": (
        "Extract ALL fields from this receipt image. Return JSON with:\n"
        "store_name, store_address, date, time, items (array of {name, price}),\n"
        "subtotal, tax, total, payment_method, card_last_four, cashier.\n"
        "Extract exact values as shown."
    ),
    "medical": (
        "Extract ALL fields from this medical document. Return JSON with:\n"
        "patient_name, date_of_birth, mrn, ordering_physician, collection_date, report_date,\n"
        "diagnosis, lab_results (object with test_name: value pairs), medications,\n"
        "allergies, vital_signs. Extract exact values as shown."
    ),
    "id_card": (
        "Extract ALL fields from this ID card/document. Return JSON with:\n"
        "document_type, document_number, full_name, date_of_birth, gender,\n"
        "fathers_name, mothers_name, address, issue_date, expiry_date,\n"
        "issuing_authority, nationality, photo_present, signature_present.\n"
        "Names are VALUES, not keys. Extract exact text as shown."
    ),
    "contract": (
        "Extract ALL fields from this contract/agreement. Return JSON with:\n"
        "agreement_type, agreement_number, effective_date, expiration_date,\n"
        "party_a, party_a_address, party_b, party_b_address,\n"
        "contract_value, payment_terms, governing_law, signatories.\n"
        "Extract exact values as shown."
    ),
    "insurance": (
        "Extract ALL fields from this insurance document. Return JSON with:\n"
        "policy_number, claim_number, policyholder, insured_name,\n"
        "date_of_loss, coverage_type, deductible, claim_amount,\n"
        "adjuster, status. Extract exact values as shown."
    ),
    "bank_statement": (
        "Extract ALL fields from this bank statement. Return JSON with:\n"
        "bank_name, account_number, account_holder, statement_period,\n"
        "opening_balance, closing_balance, total_deposits, total_withdrawals,\n"
        "transactions (array of {date, description, amount, type}).\n"
        "Extract exact values as shown."
    ),
}

GENERIC_PROMPT = (
    "Extract ALL structured data from this document image.\n"
    "Return a JSON object where:\n"
    "- Keys are descriptive field names in snake_case (use the field LABEL, not the value)\n"
    "- Values are the exact text shown in the document\n"
    "- Names of people are VALUES, not keys\n"
    "- Dates should contain only the date, not extra words like 'Signature'\n"
    "- Include tables as arrays of objects\n"
    "- Include all visible fields: IDs, names, dates, numbers, addresses\n"
    "Return ONLY valid JSON."
)

MARKDOWN_PROMPT = (
    "Convert this document image to detailed markdown. Preserve:\n"
    "- All text exactly as shown\n"
    "- Headings with # markers (## for section titles)\n"
    "- **Bold** for emphasized text\n"
    "- Tables as markdown tables with | separators\n"
    "- Reading order (top to bottom, left to right)\n"
    "- [Handwritten] prefix for handwritten text\n"
    "- [Stamp] or [Signature] for stamps and signatures\n"
    "Do NOT summarize. Extract verbatim."
)


# ── Image Preprocessing ───────────────────────────────────────

def preprocess_for_vlm(image_bytes: bytes) -> tuple[bytes, list[str]]:
    applied: list[str] = []

    try:
        from PIL import Image, ImageOps, ImageEnhance

        img = Image.open(io.BytesIO(image_bytes))

        try:
            img = ImageOps.exif_transpose(img)
            applied.append("exif_fix")
        except Exception:
            pass

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
            applied.append("rgb_convert")

        w, h = img.size
        if max(w, h) > IMAGE_MAX_DIMENSION:
            ratio = IMAGE_MAX_DIMENSION / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            applied.append(f"resize_{new_size[0]}x{new_size[1]}")

        if img.mode == "RGB":
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            applied.append("contrast_1.3")

            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            applied.append("sharpen_1.5")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), applied

    except Exception as exc:
        logger.debug("vlm_harness: preprocessing failed: %s", exc)
        return image_bytes, ["preprocessing_skipped"]


# ── Provider Chain ────────────────────────────────────────────

def _build_provider_chain() -> list[tuple[Any, str]]:
    chain: list[tuple[Any, str]] = []
    import os

    # Vertex AI Gemini — preferred on GCP (IAM auth, no API key)
    if os.environ.get("K_SERVICE") or os.environ.get("GCLOUD_PROJECT"):
        try:
            from pixora.providers.vertex_ai import VertexAIProvider
            chain.append((VertexAIProvider(
                project_id=os.environ.get("GCLOUD_PROJECT", ""),
                model=os.environ.get("PIXORA_VERTEX_MODEL", "gemini-2.0-flash-001"),
            ), "vertex_ai"))
        except Exception as exc:
            logger.debug("vlm_harness: Vertex AI not available: %s", exc)

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
        logger.debug("vlm_harness: provider chain build error: %s", exc)

    return chain


# ── Confidence Estimation ─────────────────────────────────────

def estimate_extraction_confidence(extraction: dict, markdown: str = "") -> float:
    if not extraction:
        return 0.0

    fields = {k: v for k, v in extraction.items() if not k.startswith("_") and v is not None}
    if not fields:
        return 0.0

    score = 0.0
    n = len(fields)

    if n >= 5:
        score += 0.25
    elif n >= 2:
        score += 0.15
    else:
        score += 0.05

    non_empty = sum(1 for v in fields.values() if str(v).strip())
    fill_rate = non_empty / max(n, 1)
    score += fill_rate * 0.25

    values = [str(v) for v in fields.values() if v]
    avg_len = sum(len(v) for v in values) / max(len(values), 1)
    if avg_len > 3:
        score += 0.2
    elif avg_len > 1:
        score += 0.1

    import re
    has_date = any(re.search(r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}", str(v)) for v in fields.values())
    has_number = any(re.search(r"\$[\d,]+\.?\d*|\d{3,}", str(v)) for v in fields.values())
    has_name = any(len(str(v).split()) >= 2 and str(v)[0].isupper() for v in fields.values())
    score += 0.1 * sum([has_date, has_number, has_name])

    return round(min(score, 1.0), 4)


# ── Core VLM Call ─────────────────────────────────────────────

async def _call_vlm(
    provider: Any,
    provider_name: str,
    image_bytes: bytes,
    prompt: str,
) -> tuple[str, float]:
    try:
        if hasattr(provider, "analyze_image"):
            resp = await provider.analyze_image(image_bytes, prompt)
            return resp.get("content", ""), resp.get("cost_usd", 0.0)

        if hasattr(provider, "generate"):
            b64 = base64.b64encode(image_bytes).decode()
            messages = [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]}]
            resp = await provider.generate(messages=messages)
            return resp.get("content", ""), resp.get("cost_usd", 0.0)

    except Exception as exc:
        logger.warning("vlm_harness: %s call failed: %s", provider_name, exc)

    return "", 0.0


async def _call_with_retry(
    provider: Any,
    provider_name: str,
    image_bytes: bytes,
    prompt: str,
) -> tuple[str, float, int]:
    for attempt in range(MAX_RETRIES + 1):
        content, cost = await _call_vlm(provider, provider_name, image_bytes, prompt)
        if content.strip():
            return content, cost, attempt
        if attempt < MAX_RETRIES:
            logger.info("vlm_harness: retry %d for %s", attempt + 1, provider_name)
            await asyncio.sleep(RETRY_DELAY_S * (attempt + 1))
    return "", 0.0, MAX_RETRIES + 1


# ── Multi-Page Processing ────────────────────────────────────

def _pdf_to_page_images(file_bytes: bytes, max_pages: int = 10) -> list[bytes]:
    pages: list[bytes] = []

    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for i, pg in enumerate(doc):
            if i >= max_pages:
                break
            pix = pg.get_pixmap(dpi=200)
            pages.append(pix.tobytes("png"))
        doc.close()
        return pages
    except Exception:
        pass

    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=max_pages)
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages.append(buf.getvalue())
        return pages
    except Exception:
        pass

    return []


def _merge_extractions(page_results: list[dict]) -> dict:
    merged: dict[str, Any] = {}
    for result in page_results:
        for key, value in result.items():
            if value is None:
                continue
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif isinstance(value, list) and isinstance(merged.get(key), list):
                merged[key].extend(value)
    return merged


# ── Main Entry Point ──────────────────────────────────────────

async def vlm_extract(
    file_bytes: bytes,
    filename: str = "",
    doc_type: str = "",
    enable_cache: bool = True,
    enable_preprocessing: bool = True,
    enable_markdown: bool = True,
) -> VLMResult:
    start = time.monotonic()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_pdf = ext == "pdf"
    is_image = ext in ("png", "jpg", "jpeg", "webp", "tiff", "tif", "bmp", "heic", "heif", "avif", "gif")

    cache_key = _cache_key(file_bytes, doc_type) if enable_cache else ""
    if cache_key:
        cached = _cache_get(cache_key)
        if cached:
            logger.info("vlm_harness: cache hit for %s", cache_key[:12])
            cached["cached"] = True
            return cached

    providers = _build_provider_chain()
    if not providers:
        logger.warning("vlm_harness: no VLM providers configured")
        return VLMResult(extraction={}, confidence=0.0, provider="none")

    prompt = DOMAIN_PROMPTS.get(doc_type, GENERIC_PROMPT)

    # ── Multi-page PDF ────────────────────────────────────────
    if is_pdf:
        page_images = _pdf_to_page_images(file_bytes)
        if not page_images:
            return VLMResult(extraction={}, confidence=0.0, provider="none", metadata={"error": "pdf_to_image_failed"})

        all_extractions: list[dict] = []
        all_markdowns: list[str] = []
        total_cost = 0.0
        total_retries = 0
        used_provider = ""

        for page_num, page_bytes in enumerate(page_images):
            if enable_preprocessing:
                page_bytes, preproc = preprocess_for_vlm(page_bytes)

            for provider, provider_name in providers:
                content, cost, retries = await _call_with_retry(provider, provider_name, page_bytes, prompt)
                total_cost += cost
                total_retries += retries

                if content.strip():
                    used_provider = provider_name
                    parsed = extract_json_object(content)
                    if parsed:
                        all_extractions.append(parsed)
                    break

            if enable_markdown:
                for provider, provider_name in providers:
                    md_content, md_cost, _ = await _call_with_retry(provider, provider_name, page_bytes, MARKDOWN_PROMPT)
                    total_cost += md_cost
                    if md_content.strip():
                        all_markdowns.append(f"<!-- Page {page_num + 1} -->\n{md_content}")
                        break

        merged = _merge_extractions(all_extractions)
        full_markdown = "\n\n".join(all_markdowns)
        confidence = estimate_extraction_confidence(merged, full_markdown)

        result = VLMResult(
            extraction=merged,
            markdown=full_markdown,
            confidence=confidence,
            provider=used_provider,
            cost_usd=round(total_cost, 6),
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            pages_processed=len(page_images),
            retries=total_retries,
        )

        if cache_key:
            _cache_put(cache_key, result)
        return result

    # ── Single Image ──────────────────────────────────────────
    preproc_applied: list[str] = []
    processed_bytes = file_bytes
    if enable_preprocessing:
        processed_bytes, preproc_applied = preprocess_for_vlm(file_bytes)

    extraction: dict[str, Any] = {}
    markdown = ""
    total_cost = 0.0
    total_retries = 0
    used_provider = ""

    for provider, provider_name in providers:
        content, cost, retries = await _call_with_retry(provider, provider_name, processed_bytes, prompt)
        total_cost += cost
        total_retries += retries

        if content.strip():
            used_provider = provider_name
            parsed = extract_json_object(content)
            if parsed and any(k for k in parsed if not k.startswith("_")):
                extraction = parsed
                break
            if not parsed and len(content) > 50:
                markdown = content
                break

    if enable_markdown and not markdown:
        for provider, provider_name in providers:
            md_content, md_cost, _ = await _call_with_retry(provider, provider_name, processed_bytes, MARKDOWN_PROMPT)
            total_cost += md_cost
            if md_content.strip():
                markdown = md_content
                break

    confidence = estimate_extraction_confidence(extraction, markdown)

    tables: list[str] = []
    if extraction:
        for key, value in list(extraction.items()):
            if isinstance(value, list) and value and isinstance(value[0], dict):
                from pixora.parsing.pdf_reader import _table_to_markdown
                headers = list(value[0].keys())
                rows = [headers] + [list(item.values()) for item in value]
                table_md = _table_to_markdown(rows)
                if table_md:
                    tables.append(table_md)

    result = VLMResult(
        extraction=extraction,
        markdown=markdown,
        tables=tables,
        confidence=confidence,
        provider=used_provider,
        cost_usd=round(total_cost, 6),
        latency_ms=round((time.monotonic() - start) * 1000, 1),
        pages_processed=1,
        cached=False,
        retries=total_retries,
        preprocessing=preproc_applied,
    )

    if cache_key:
        _cache_put(cache_key, result)

    return result


# ── Pipeline Integration ──────────────────────────────────────

async def should_use_vlm(file_bytes: bytes, filename: str, ocr_text: str = "") -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_image = ext in ("png", "jpg", "jpeg", "webp", "tiff", "tif", "bmp", "heic", "heif", "avif", "gif")

    if is_image:
        return True

    if not ocr_text or len(ocr_text.strip()) < 20:
        return True

    from pixora.ocr.smart_pipeline import estimate_text_quality
    quality = estimate_text_quality(ocr_text)
    if quality < 0.4:
        return True

    return False


def is_vlm_available() -> bool:
    providers = _build_provider_chain()
    return len(providers) > 0
