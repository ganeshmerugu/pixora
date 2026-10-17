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
    "Return a JSON object with two keys:\n\n"
    "1. \"fields\": object where keys are field names in snake_case and values are the exact text\n"
    "2. \"bboxes\": object where keys are the SAME field names and values are "
    "{\"left\": 0.xx, \"top\": 0.xx, \"right\": 0.xx, \"bottom\": 0.xx} "
    "as fractions (0-1) of the image width/height showing WHERE the value appears\n\n"
    "Rules:\n"
    "- Names of people are VALUES, not keys\n"
    "- Dates should contain only the date\n"
    "- Include all visible fields: IDs, names, dates, numbers, addresses\n\n"
    "Example:\n"
    "{\"fields\": {\"name\": \"John Doe\", \"date\": \"03/15/2024\"}, "
    "\"bboxes\": {\"name\": {\"left\": 0.3, \"top\": 0.15, \"right\": 0.7, \"bottom\": 0.18}, "
    "\"date\": {\"left\": 0.7, \"top\": 0.15, \"right\": 0.9, \"bottom\": 0.18}}}\n\n"
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


# ── Enterprise Image Preprocessing ────────────────────────────

def preprocess_for_vlm(image_bytes: bytes) -> tuple[bytes, list[str]]:
    """Full pipeline: EXIF → rotate → deskew → shadow remove → denoise →
    CLAHE contrast → sharpen → border remove → DPI upscale → resize."""
    applied: list[str] = []

    try:
        from PIL import Image, ImageOps, ImageEnhance
        import numpy as np

        img = Image.open(io.BytesIO(image_bytes))

        # 1. EXIF
        try:
            img = ImageOps.exif_transpose(img)
            applied.append("exif")
        except Exception:
            pass

        # 2. RGB
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
            applied.append("rgb")

        # 3. Rotation detect (90/180)
        img, rot = _detect_rotation(img)
        if rot:
            applied.append(f"rotate_{rot}")

        # OpenCV path (full enterprise pipeline)
        try:
            import cv2
            arr = np.array(img)

            # 4. Deskew
            arr, angle = _deskew(arr)
            if abs(angle) > 0.5:
                applied.append(f"deskew_{angle:.1f}")

            # 5. Shadow removal
            arr = _remove_shadows(arr)
            applied.append("deshadow")

            # 6. Denoise (NLM)
            if len(arr.shape) == 3:
                arr = cv2.fastNlMeansDenoisingColored(arr, None, h=6, hForColorComponents=6, templateWindowSize=7, searchWindowSize=21)
            else:
                arr = cv2.fastNlMeansDenoising(arr, None, h=6, templateWindowSize=7, searchWindowSize=21)
            applied.append("denoise")

            # 7. CLAHE contrast
            if len(arr.shape) == 3:
                lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
                clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                arr = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
            else:
                arr = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(arr)
            applied.append("clahe")

            # 8. Sharpen
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            arr = cv2.filter2D(arr, -1, kernel)
            applied.append("sharpen")

            # 9. Border removal
            arr, trimmed = _remove_borders(arr)
            if trimmed:
                applied.append("deborder")

            img = Image.fromarray(arr)

        except ImportError:
            img = ImageEnhance.Contrast(img).enhance(1.4)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            applied.append("pil_fallback")

        # 10. DPI upscale (min 1500px short side)
        w, h = img.size
        if min(w, h) < 1500:
            scale = 1500 / min(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            applied.append("upscale")

        # 11. Cap max for API
        w, h = img.size
        if max(w, h) > IMAGE_MAX_DIMENSION:
            ratio = IMAGE_MAX_DIMENSION / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            applied.append("cap")

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), applied

    except Exception as exc:
        logger.debug("vlm_harness: preprocessing failed: %s", exc)
        return image_bytes, ["skipped"]


def _detect_rotation(img):
    try:
        import numpy as np
        arr = np.array(img.convert("L"))
        h, w = arr.shape
        if w < h * 0.6:
            return img.rotate(-90, expand=True), 90
        top = np.count_nonzero(arr[:h // 2] < 128)
        bot = np.count_nonzero(arr[h // 2:] < 128)
        if bot > top * 2.0 and h > 200:
            return img.rotate(180, expand=True), 180
    except Exception:
        pass
    return img, 0


def _deskew(arr):
    import cv2, numpy as np
    try:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if len(arr.shape) == 3 else arr
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        if lines is None:
            return arr, 0.0
        angles = [np.degrees(np.arctan2(l[0][3] - l[0][1], l[0][2] - l[0][0])) for l in lines]
        angles = [a for a in angles if abs(a) < 45]
        if not angles:
            return arr, 0.0
        med = float(np.median(angles))
        if abs(med) < 0.5:
            return arr, 0.0
        h, w = arr.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), med, 1.0)
        return cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), med
    except Exception:
        return arr, 0.0


def _remove_shadows(arr):
    import cv2, numpy as np
    try:
        if len(arr.shape) == 3:
            planes = cv2.split(arr)
            result = []
            for p in planes:
                bg = cv2.medianBlur(cv2.dilate(p, np.ones((7, 7), np.uint8)), 21)
                diff = 255 - cv2.absdiff(p, bg)
                result.append(cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1))
            return cv2.merge(result)
        else:
            bg = cv2.medianBlur(cv2.dilate(arr, np.ones((7, 7), np.uint8)), 21)
            diff = 255 - cv2.absdiff(arr, bg)
            return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
    except Exception:
        return arr


def _remove_borders(arr):
    import cv2, numpy as np
    try:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if len(arr.shape) == 3 else arr
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return arr, False
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        ih, iw = arr.shape[:2]
        if w > iw * 0.5 and h > ih * 0.5:
            m = 5
            return arr[max(0, y - m):min(ih, y + h + m), max(0, x - m):min(iw, x + w + m)], True
    except Exception:
        pass
    return arr, False


# ── Provider Chain ────────────────────────────────────────────

def _build_provider_chain() -> list[tuple[Any, str]]:
    from pixora.providers.provider_chain import get_vlm_chain
    return get_vlm_chain()


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
        exc_str = str(exc)
        logger.warning("vlm_harness: %s call failed: %s", provider_name, exc_str)
        if "429" in exc_str:
            return "__RATE_LIMITED__", 0.0
    return "", 0.0


async def _call_with_retry(
    provider: Any,
    provider_name: str,
    image_bytes: bytes,
    prompt: str,
) -> tuple[str, float, int]:
    for attempt in range(MAX_RETRIES + 1):
        content, cost = await _call_vlm(provider, provider_name, image_bytes, prompt)
        if content == "__RATE_LIMITED__":
            wait = (attempt + 1) * 5
            logger.info("vlm_harness: 429 rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
            await asyncio.sleep(wait)
            continue
        if content.strip():
            return content, cost, attempt
        if attempt < MAX_RETRIES:
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
    vlm_bboxes: dict[str, dict] = {}
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
            if parsed:
                # New format: {"fields": {...}, "bboxes": {...}}
                if "fields" in parsed and isinstance(parsed["fields"], dict):
                    extraction = parsed["fields"]
                    vlm_bboxes = parsed.get("bboxes", {})
                elif any(k for k in parsed if not k.startswith("_")):
                    extraction = parsed
                    vlm_bboxes = {}

                if extraction:
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

    if vlm_bboxes:
        result["metadata"] = {"vlm_bboxes": vlm_bboxes}

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
