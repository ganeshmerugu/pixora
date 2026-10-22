"""Smart OCR pipeline — quality-aware extraction with automatic escalation.

Flow:
1. Direct text extraction (PyMuPDF) → check quality
2. If low → preprocess image + OCR (EasyOCR) + postprocess (confusion fix)
3. If still low → VLM escalation (serverless API, ~$0.003/page)

Quality is measured by: character density, word count, digit-to-noise ratio,
and extraction confidence. No LLM needed for quality estimation.
"""
from __future__ import annotations
import io
import logging
import re
import time
from typing import Any
from typing_extensions import Required, TypedDict

logger = logging.getLogger(__name__)


class ExtractionResult(TypedDict, total=False):
    text: Required[str]
    markdown: str
    method: Required[str]
    confidence: float
    quality_score: float
    cost_usd: float
    latency_ms: float
    preprocessing_applied: list[str]
    postprocessing_applied: list[str]
    escalation_reason: str
    metadata: dict[str, Any]


QUALITY_THRESHOLD_OCR = 0.4
QUALITY_THRESHOLD_VLM = 0.3


def estimate_text_quality(text: str) -> float:
    if not text or not text.strip():
        return 0.0

    length = len(text.strip())
    if length < 20:
        return 0.1

    words = text.split()
    word_count = len(words)
    if word_count < 5:
        return 0.15

    alpha_chars = sum(1 for c in text if c.isalpha())
    digit_chars = sum(1 for c in text if c.isdigit())
    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars == 0:
        return 0.0

    alpha_ratio = alpha_chars / total_chars
    if alpha_ratio < 0.3:
        return 0.2

    avg_word_len = sum(len(w) for w in words) / word_count
    if avg_word_len < 2 or avg_word_len > 25:
        return 0.25

    garbage_pattern = re.compile(r"[^\x20-\x7E\n\t\rÀ-ɏЀ-ӿऀ-ॿ一-鿿]")
    garbage_chars = len(garbage_pattern.findall(text))
    garbage_ratio = garbage_chars / total_chars
    if garbage_ratio > 0.15:
        return 0.2

    unique_words = set(w.lower() for w in words if w.isalpha())
    diversity = len(unique_words) / max(word_count, 1)

    score = 0.0
    score += min(alpha_ratio * 0.8, 0.3)
    score += min(word_count / 100, 0.25)
    score += min(diversity * 0.5, 0.2)
    score += 0.15 if digit_chars > 0 else 0.0
    score += 0.1 if avg_word_len > 3 else 0.0
    score -= garbage_ratio * 0.5

    ocr_penalty = _detect_ocr_corruption(text, words)
    score -= ocr_penalty

    dict_penalty = _dictionary_check(words)
    score -= dict_penalty

    return round(max(0.0, min(1.0, score)), 4)


def _dictionary_check(words: list[str]) -> float:
    from pixora.ocr.postprocessor import DOMAIN_DICTIONARIES
    all_terms = DOMAIN_DICTIONARIES.get("default", frozenset())

    _COMMON_WORDS = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "ought",
        "and", "or", "but", "not", "no", "nor", "so", "for", "yet", "both",
        "if", "then", "else", "when", "where", "while", "as", "of", "to",
        "in", "on", "at", "by", "from", "with", "into", "through", "during",
        "before", "after", "above", "below", "between", "under", "again",
        "this", "that", "these", "those", "it", "its", "they", "them", "their",
        "we", "our", "you", "your", "he", "she", "his", "her", "i", "me", "my",
        "all", "each", "every", "any", "some", "most", "other", "such", "only",
        "per", "up", "out", "off", "over", "also", "very", "just", "than",
        "more", "less", "too", "here", "there", "now", "how", "what", "which",
        "who", "whom", "whose", "why", "name", "date", "number", "total",
        "page", "new", "old", "first", "last", "next", "see", "one", "two",
    })

    check_words = [w.lower() for w in words if w.isalpha() and len(w) > 3]
    if len(check_words) < 5:
        return 0.0

    known = sum(1 for w in check_words if w in all_terms or w in _COMMON_WORDS)
    known_ratio = known / len(check_words)

    if known_ratio > 0.5:
        return 0.0
    elif known_ratio > 0.3:
        return 0.15
    elif known_ratio > 0.15:
        return 0.3
    else:
        return 0.45


def _detect_ocr_corruption(text: str, words: list[str]) -> float:
    penalty = 0.0

    ocr_confused = re.findall(r"[A-Za-z]\d[A-Za-z]|\d[A-Za-z]\d", text)
    if len(ocr_confused) > 3:
        penalty += min(len(ocr_confused) * 0.03, 0.25)

    nonsense = sum(1 for w in words if len(w) > 2 and w.isalpha() and
                   not re.match(r"^[a-zA-Z]+$", w) and
                   sum(1 for c in w if c.isupper()) > len(w) * 0.5 and
                   len(w) < 15)
    if nonsense > 2:
        penalty += min(nonsense * 0.02, 0.15)

    digit_letter_mix = sum(1 for w in words if
                           any(c.isdigit() for c in w) and
                           any(c.isalpha() for c in w) and
                           not re.match(r"^[A-Z]{1,5}[-#]?\d+$", w) and
                           not re.match(r"^\d+[a-zA-Z]{1,3}$", w) and
                           len(w) > 3)
    if digit_letter_mix > 5:
        penalty += min(digit_letter_mix * 0.02, 0.2)

    common_confusions = len(re.findall(r"(?:rn|vv|cl|li|ii)(?=[a-z])", text.lower()))
    if common_confusions > 3:
        penalty += min(common_confusions * 0.02, 0.15)

    broken_amounts = len(re.findall(r"\$[\dOolI,]+\.[\dOolI]", text))
    broken_dates = len(re.findall(r"\b[\dOolI]{1,2}[/\-][\dOolI]{1,2}[/\-][\dOolI]{2,4}\b", text))
    if broken_amounts > 0 or broken_dates > 0:
        penalty += (broken_amounts + broken_dates) * 0.05

    return min(penalty, 0.6)


def apply_postprocessing(text: str, doc_type: str = "") -> tuple[str, list[str]]:
    applied: list[str] = []

    from pixora.ocr.postprocessor import (
        COMMON_OCR_CONFUSIONS, REVERSE_CONFUSIONS, UNICODE_LOOKALIKES,
        DOMAIN_DICTIONARIES,
    )

    changed = False
    result = []
    for c in text:
        if c in UNICODE_LOOKALIKES:
            result.append(UNICODE_LOOKALIKES[c])
            changed = True
        else:
            result.append(c)
    if changed:
        text = "".join(result)
        applied.append("unicode_normalization")

    domain_dict = DOMAIN_DICTIONARIES.get(doc_type, DOMAIN_DICTIONARIES.get("default", frozenset()))

    words = text.split()
    corrected_words: list[str] = []
    confusion_fixes = 0

    for word in words:
        fixed = word
        word_lower = word.lower()

        if len(word) > 2 and not any(c.isdigit() for c in word):
            for wrong, right in COMMON_OCR_CONFUSIONS.items():
                if wrong in word_lower:
                    candidate = word_lower.replace(wrong, right)
                    if candidate in domain_dict and word_lower not in domain_dict:
                        fixed = candidate
                        confusion_fixes += 1
                        break

        corrected_words.append(fixed)

    if confusion_fixes > 0:
        text = " ".join(corrected_words)
        applied.append(f"confusion_fix:{confusion_fixes}")

    amount_re = re.compile(r"\$[\dOolI,]+\.[\dOolI]{2}")
    for m in amount_re.finditer(text):
        original = m.group()
        fixed = original.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
        if fixed != original:
            text = text.replace(original, fixed)
            applied.append("amount_fix")

    date_re = re.compile(r"\b[\dOolI]{1,2}[/\-\.I][\dOolI]{1,2}[/\-\.I][\dOolI]{2,4}\b")
    for m in date_re.finditer(text):
        original = m.group()
        fixed = original.replace("O", "0").replace("o", "0").replace("l", "1")
        fixed = re.sub(r"(\d)I(\d)", r"\1/\2", fixed)
        fixed = fixed.replace("I", "1")
        if fixed != original:
            text = text.replace(original, fixed)
            applied.append("date_fix")

    id_re = re.compile(r"\b[A-Z]{2,5}[-#][\dOolI]{3,}")
    for m in id_re.finditer(text):
        original = m.group()
        prefix_end = original.index("-") + 1 if "-" in original else original.index("#") + 1
        prefix = original[:prefix_end]
        num_part = original[prefix_end:]
        fixed_num = num_part.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
        if fixed_num != num_part:
            text = text.replace(original, prefix + fixed_num)
            applied.append("id_fix")

    return text, applied


async def preprocess_and_ocr(image_bytes: bytes) -> tuple[str, list[str]]:
    applied: list[str] = []

    try:
        from PIL import Image
        from pixora.ocr.preprocessing import (
            PreprocessingPipeline, DEFAULT_CONFIG, fix_exif_orientation,
            validate_image_bytes,
        )

        validation = validate_image_bytes(image_bytes)
        if not validation["valid"]:
            return "", [f"invalid_image:{validation.get('reason', 'unknown')}"]

        image = Image.open(io.BytesIO(image_bytes))

        image, exif_fixed = fix_exif_orientation(image)
        if exif_fixed:
            applied.append("exif_fix")

        pipeline = PreprocessingPipeline()
        config = {**DEFAULT_CONFIG, "deskew": True, "noise_removal": True, "contrast": True, "binarization": False}
        result = pipeline.process(image, config)
        preprocessed_image = result["image"]
        applied.extend(result.get("transforms_applied", []))

        buf = io.BytesIO()
        preprocessed_image.save(buf, format="PNG")
        processed_bytes = buf.getvalue()
    except Exception as exc:
        logger.warning("smart_pipeline: preprocessing failed: %s", exc)
        processed_bytes = image_bytes
        applied.append("preprocessing_skipped")

    try:
        from pixora.ocr.easyocr_engine import EasyOCREngine
        engine = EasyOCREngine()
        regions = await engine.recognize(processed_bytes)
        text = " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        applied.append("easyocr")
        return text, applied
    except Exception as exc:
        logger.warning("smart_pipeline: EasyOCR failed: %s", exc)
        return "", applied + ["easyocr_failed"]


VLM_DOCUMENT_PROMPT = (
    "Extract ALL text from this document image precisely. Rules:\n"
    "1. Preserve exact layout, reading order, and formatting\n"
    "2. Output as clean markdown with ## headings, **bold**, *italic*\n"
    "3. Reproduce tables as markdown tables with | column | separators |\n"
    "4. Include ALL numbers, dates, amounts, IDs exactly as shown\n"
    "5. Mark handwritten text with [Handwritten] prefix\n"
    "6. Note stamps/signatures as [Stamp] or [Signature]\n"
    "7. Do NOT summarize — extract verbatim"
)


def _get_vlm_provider(explicit_provider: Any = None):
    if explicit_provider:
        return explicit_provider, "explicit"
    from pixora.providers.provider_chain import get_best_provider
    return get_best_provider()


async def vlm_extract(
    image_bytes: bytes,
    prompt: str = "",
    provider: Any = None,
) -> tuple[str, float]:
    provider, provider_name = _get_vlm_provider(provider)

    if not provider:
        logger.info("smart_pipeline: no VLM provider configured — set PIXORA_GEMINI_API_KEY (free) or PIXORA_GROQ_API_KEY")
        return "", 0.0

    if not prompt:
        prompt = VLM_DOCUMENT_PROMPT

    logger.info("smart_pipeline: VLM escalation via %s", provider_name)

    try:
        if hasattr(provider, "analyze_image"):
            resp = await provider.analyze_image(image_bytes, prompt)
            cost = resp.get("cost_usd", 0.0)
            return resp.get("content", ""), cost
    except Exception as exc:
        logger.warning("smart_pipeline: VLM analyze_image failed (%s): %s", provider_name, exc)

    try:
        if hasattr(provider, "generate"):
            import base64
            b64 = base64.b64encode(image_bytes).decode()
            messages = [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]}]
            resp = await provider.generate(messages=messages)
            cost = resp.get("cost_usd", 0.0)
            return resp.get("content", ""), cost
    except Exception as exc:
        logger.warning("smart_pipeline: VLM generate failed (%s): %s", provider_name, exc)

    return "", 0.0


async def smart_extract(
    file_bytes: bytes,
    filename: str = "document.pdf",
    doc_type: str = "",
    vlm_provider: Any = None,
    enable_vlm: bool = True,
) -> ExtractionResult:
    start = time.monotonic()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    total_cost = 0.0

    # ── Strategy 1: Direct text extraction (free, fast) ────────
    text = ""
    method = "direct"

    if ext == "pdf":
        text = _try_pymupdf_text(file_bytes)
        if not text:
            text = _try_pdfplumber_text(file_bytes)

    quality = estimate_text_quality(text)
    logger.info("smart_pipeline: direct extraction quality=%.2f len=%d", quality, len(text))

    if quality >= QUALITY_THRESHOLD_OCR:
        text, post_applied = apply_postprocessing(text, doc_type)
        return ExtractionResult(
            text=text, method="direct_text", confidence=quality,
            quality_score=quality, cost_usd=0.0,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            postprocessing_applied=post_applied,
        )

    # ── Strategy 2: Preprocess + OCR (free, slower) ───────────
    image_bytes = _file_to_image_bytes(file_bytes, ext)
    if image_bytes:
        ocr_text, preprocess_applied = await preprocess_and_ocr(image_bytes)
        ocr_quality = estimate_text_quality(ocr_text)
        logger.info("smart_pipeline: OCR quality=%.2f len=%d", ocr_quality, len(ocr_text))

        if ocr_quality > quality:
            text = ocr_text
            quality = ocr_quality
            method = "preprocessed_ocr"

        text, post_applied = apply_postprocessing(text, doc_type)
        quality = estimate_text_quality(text)

        if quality >= QUALITY_THRESHOLD_VLM or not enable_vlm:
            return ExtractionResult(
                text=text, method=method, confidence=quality,
                quality_score=quality, cost_usd=0.0,
                latency_ms=round((time.monotonic() - start) * 1000, 1),
                preprocessing_applied=preprocess_applied,
                postprocessing_applied=post_applied,
            )

    # ── Strategy 3: VLM escalation (~$0.003/page) ─────────────
    if enable_vlm and image_bytes:
        vlm_text, vlm_cost = await vlm_extract(image_bytes, provider=vlm_provider)
        total_cost += vlm_cost

        if vlm_text:
            vlm_quality = estimate_text_quality(vlm_text)
            logger.info("smart_pipeline: VLM quality=%.2f len=%d cost=$%.4f", vlm_quality, len(vlm_text), vlm_cost)

            if vlm_quality > quality:
                vlm_text, post_applied = apply_postprocessing(vlm_text, doc_type)
                return ExtractionResult(
                    text=vlm_text, markdown=vlm_text, method="vlm_escalation",
                    confidence=vlm_quality, quality_score=vlm_quality,
                    cost_usd=round(total_cost, 6),
                    latency_ms=round((time.monotonic() - start) * 1000, 1),
                    postprocessing_applied=post_applied,
                    escalation_reason=f"quality {quality:.2f} < threshold {QUALITY_THRESHOLD_VLM}",
                )

    # ── Fallback: return best we have ──────────────────────────
    text, post_applied = apply_postprocessing(text, doc_type)
    return ExtractionResult(
        text=text, method=method or "fallback", confidence=quality,
        quality_score=quality, cost_usd=round(total_cost, 6),
        latency_ms=round((time.monotonic() - start) * 1000, 1),
        postprocessing_applied=post_applied,
    )


def _try_pymupdf_text(data: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        texts = []
        for pg in doc:
            blocks = pg.get_text("dict", sort=True).get("blocks", [])
            for b in sorted(blocks, key=lambda x: (x.get("bbox", [0])[1], x.get("bbox", [0])[0])):
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    spans_text = "".join(s.get("text", "") for s in line.get("spans", []))
                    if spans_text.strip():
                        texts.append(spans_text)
        doc.close()
        return "\n".join(texts)
    except Exception:
        return ""


def _try_pdfplumber_text(data: bytes) -> str:
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pg in pdf.pages:
                try:
                    text = pg.extract_text(layout=True) or ""
                except TypeError:
                    text = pg.extract_text() or ""
                if text.strip():
                    texts.append(text)
        return "\n\n".join(texts)
    except Exception:
        return ""


def _file_to_image_bytes(data: bytes, ext: str) -> bytes:
    if ext in ("png", "jpg", "jpeg", "tiff", "tif", "bmp", "webp"):
        return data

    if ext == "pdf":
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(data, dpi=200, first_page=1, last_page=1)
            if images:
                buf = io.BytesIO()
                images[0].save(buf, format="PNG")
                return buf.getvalue()
        except Exception:
            pass

        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            if doc.page_count > 0:
                pix = doc[0].get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                doc.close()
                return img_bytes
        except Exception:
            pass

    return b""
