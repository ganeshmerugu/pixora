"""Unified Document Processing Pipeline — OCR engines + VLM brain, working together.

Architecture:
  - Digital PDFs: text extraction first (free), VLM only if needed
  - Scanned/Images: preprocess → parallel OCR → quality check → VLM enrichment
  - OCR provides: exact text, bounding boxes, word confidence
  - VLM provides: semantic understanding, field extraction, structure
  - Merged result: OCR positions + VLM intelligence

This is the enterprise pipeline that uses EVERYTHING we built.
"""
from __future__ import annotations
import asyncio
import io
import logging
import time
from typing import Any
from typing_extensions import Required, TypedDict

logger = logging.getLogger(__name__)


class UnifiedResult(TypedDict, total=False):
    text: Required[str]
    markdown: str
    extraction: dict[str, Any]
    tables: list[str]
    method: Required[str]
    ocr_text: str
    ocr_confidence: float
    ocr_words: list[dict]
    vlm_extraction: dict[str, Any]
    vlm_markdown: str
    vlm_confidence: float
    final_confidence: float
    cost_usd: float
    latency_ms: float
    engines_used: list[str]
    preprocessing: list[str]
    quality_scores: dict[str, float]


async def process_document(
    file_bytes: bytes,
    filename: str,
    doc_type: str = "",
    enable_vlm: bool = True,
    enable_preprocessing: bool = True,
) -> UnifiedResult:
    start = time.monotonic()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_pdf = ext == "pdf"
    is_image = ext in ("png", "jpg", "jpeg", "webp", "tiff", "tif", "bmp", "heic", "heif", "avif", "gif")
    engines_used: list[str] = []
    total_cost = 0.0

    # ══════════════════════════════════════════════════════════
    # BRANCH 1: Digital PDF (has text layer)
    # ══════════════════════════════════════════════════════════
    if is_pdf:
        text, md, pdf_method = await _extract_pdf_text(file_bytes)
        if text and len(text.strip()) > 30:
            engines_used.append(pdf_method)
            from pixora.ocr.smart_pipeline import estimate_text_quality
            quality = estimate_text_quality(text)

            if quality >= 0.6 or not enable_vlm:
                return UnifiedResult(
                    text=text, markdown=md or text, method=f"pdf_{pdf_method}",
                    ocr_text=text, ocr_confidence=quality,
                    final_confidence=quality, cost_usd=0.0,
                    latency_ms=round((time.monotonic() - start) * 1000, 1),
                    engines_used=engines_used,
                    quality_scores={"text_quality": quality},
                )

            # Quality too low — enrich with VLM
            vlm_result = await _vlm_enrich(file_bytes, filename, doc_type, text)
            if vlm_result:
                total_cost += vlm_result.get("cost_usd", 0)
                engines_used.append(f"vlm_{vlm_result.get('provider', '?')}")
                merged = _merge_ocr_vlm(text, quality, vlm_result)
                merged["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
                merged["engines_used"] = engines_used
                merged["cost_usd"] = total_cost
                return merged

            return UnifiedResult(
                text=text, markdown=md or text, method=f"pdf_{pdf_method}",
                ocr_text=text, ocr_confidence=quality,
                final_confidence=quality, cost_usd=0.0,
                latency_ms=round((time.monotonic() - start) * 1000, 1),
                engines_used=engines_used,
            )

    # ══════════════════════════════════════════════════════════
    # BRANCH 2: Scanned PDF / Image
    # ══════════════════════════════════════════════════════════

    # Step 1: Preprocess
    processed_bytes = file_bytes
    preproc_applied: list[str] = []
    if enable_preprocessing and is_image:
        processed_bytes, preproc_applied = _preprocess_image(file_bytes)

    if is_pdf:
        processed_bytes = _pdf_first_page_to_image(file_bytes)
        if not processed_bytes:
            processed_bytes = file_bytes

    # Step 2: Parallel OCR (run all available engines simultaneously)
    ocr_text, ocr_confidence, ocr_words, ocr_engines = await _parallel_ocr(processed_bytes)
    engines_used.extend(ocr_engines)

    # Step 3: Postprocess OCR text (confusion pairs, amount/date fixes)
    if ocr_text:
        from pixora.ocr.smart_pipeline import apply_postprocessing
        ocr_text, postproc_applied = apply_postprocessing(ocr_text, doc_type)
        preproc_applied.extend(postproc_applied)

    from pixora.ocr.smart_pipeline import estimate_text_quality
    ocr_quality = estimate_text_quality(ocr_text) if ocr_text else 0.0

    # Step 4: Decide — OCR good enough, or need VLM?
    if ocr_quality >= 0.6 and not enable_vlm:
        return UnifiedResult(
            text=ocr_text, markdown=ocr_text, method="ocr_only",
            ocr_text=ocr_text, ocr_confidence=ocr_quality, ocr_words=ocr_words,
            final_confidence=ocr_quality, cost_usd=0.0,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            engines_used=engines_used, preprocessing=preproc_applied,
            quality_scores={"ocr_quality": ocr_quality},
        )

    # Step 5: VLM extraction (on original image, not preprocessed — VLM handles its own preprocessing)
    vlm_result = await _vlm_enrich(file_bytes, filename, doc_type, ocr_text)

    if vlm_result and vlm_result.get("extraction"):
        total_cost += vlm_result.get("cost_usd", 0)
        engines_used.append(f"vlm_{vlm_result.get('provider', '?')}")

        # Step 6: Merge OCR + VLM
        merged = _merge_ocr_vlm(ocr_text, ocr_quality, vlm_result)
        merged["ocr_words"] = ocr_words
        merged["preprocessing"] = preproc_applied
        merged["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
        merged["engines_used"] = engines_used
        merged["cost_usd"] = total_cost
        return merged

    # Step 7: VLM unavailable — return OCR result
    if ocr_text and ocr_text.strip():
        return UnifiedResult(
            text=ocr_text, markdown=ocr_text, method="ocr_fallback",
            ocr_text=ocr_text, ocr_confidence=ocr_quality, ocr_words=ocr_words,
            final_confidence=ocr_quality, cost_usd=0.0,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            engines_used=engines_used, preprocessing=preproc_applied,
        )

    # Step 8: Nothing worked
    return UnifiedResult(
        text="", method="failed", final_confidence=0.0,
        cost_usd=total_cost,
        latency_ms=round((time.monotonic() - start) * 1000, 1),
        engines_used=engines_used,
    )


# ── PDF Text Extraction (free, fast) ─────────────────────────

async def _extract_pdf_text(file_bytes: bytes) -> tuple[str, str, str]:
    # Try docling first (best markdown)
    try:
        from pixora.extraction.docling_engine import extract_with_docling
        result = extract_with_docling(file_bytes, "document.pdf")
        md = result.get("markdown", "")
        text = result.get("text", md)
        if md.strip() and len(md.strip()) > 30:
            return text, md, "docling"
    except Exception:
        pass

    # Try PyMuPDF font-aware (bold/italic/headings)
    try:
        from pixora.evals.parsebench.runner import PixoraParseBenchRunner
        runner = PixoraParseBenchRunner()
        md = runner._try_pymupdf_markdown(file_bytes)
        if md and len(md.strip()) > 30:
            return md, md, "pymupdf_markdown"
    except Exception:
        pass

    # Try pdfplumber layout-aware
    try:
        from pixora.parsing.pdf_reader import PDFReader
        reader = PDFReader()
        tree = await reader.read(file_bytes, "document.pdf")
        texts = []
        for page in tree.get("pages", []):
            for region in sorted(page.get("regions", []),
                                 key=lambda r: (r.get("reading_order", 0), r.get("bbox", {}).get("y", 0))):
                c = region.get("content", "")
                if c.strip():
                    texts.append(c)
        text = "\n\n".join(texts)
        if text.strip():
            return text, text, "pdfplumber"
    except Exception:
        pass

    return "", "", "none"


# ── Image Preprocessing ───────────────────────────────────────

def _preprocess_image(image_bytes: bytes) -> tuple[bytes, list[str]]:
    try:
        from pixora.ocr.vlm_harness import preprocess_for_vlm
        return preprocess_for_vlm(image_bytes)
    except Exception:
        return image_bytes, []


def _pdf_first_page_to_image(file_bytes: bytes) -> bytes:
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.page_count > 0:
            pix = doc[0].get_pixmap(dpi=200)
            result = pix.tobytes("png")
            doc.close()
            return result
    except Exception:
        pass

    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=1)
        if images:
            buf = io.BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        pass

    return b""


# ── Parallel OCR ──────────────────────────────────────────────

async def _parallel_ocr(
    image_bytes: bytes,
) -> tuple[str, float, list[dict], list[str]]:
    if not image_bytes:
        return "", 0.0, [], []

    from PIL import Image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except Exception:
        png_bytes = image_bytes

    tasks = []
    engine_names: list[str] = []

    # EasyOCR (always available)
    try:
        from pixora.ocr.easyocr_engine import EasyOCREngine

        async def run_easyocr():
            engine = EasyOCREngine()
            return await engine.recognize(png_bytes)
        tasks.append(run_easyocr())
        engine_names.append("easyocr")
    except ImportError:
        pass

    # Tesseract
    try:
        from pixora.ocr.tesseract import TesseractEngine

        async def run_tesseract():
            engine = TesseractEngine()
            return await engine.recognize(png_bytes)
        tasks.append(run_tesseract())
        engine_names.append("tesseract")
    except Exception:
        pass

    # PaddleOCR
    try:
        from pixora.ocr.paddle_engine import PaddleOCREngine

        async def run_paddle():
            engine = PaddleOCREngine()
            return await engine.recognize(png_bytes)
        tasks.append(run_paddle())
        engine_names.append("paddleocr")
    except Exception:
        pass

    if not tasks:
        return "", 0.0, [], []

    results = await asyncio.gather(*tasks, return_exceptions=True)

    best_text = ""
    best_confidence = 0.0
    best_words: list[dict] = []
    used_engines: list[str] = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.debug("unified_pipeline: %s failed: %s", engine_names[i], result)
            continue

        if not result:
            continue

        text = " ".join(r.get("text", "") for r in result if r.get("text", "").strip())
        conf = sum(r.get("confidence", 0) for r in result) / max(len(result), 1)
        words = []
        for r in result:
            words.extend(r.get("words", []))

        if len(text) > len(best_text) or (len(text) == len(best_text) and conf > best_confidence):
            best_text = text
            best_confidence = conf
            best_words = words
            used_engines = [engine_names[i]]

    return best_text, best_confidence, best_words, used_engines


# ── VLM Enrichment ────────────────────────────────────────────

async def _vlm_enrich(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    ocr_text: str = "",
) -> dict | None:
    try:
        from pixora.ocr.vlm_harness import vlm_extract, is_vlm_available
        if not is_vlm_available():
            return None

        result = await vlm_extract(file_bytes, filename, doc_type)
        if result.get("extraction") or result.get("markdown"):
            return result
    except Exception as exc:
        logger.debug("unified_pipeline: VLM enrichment failed: %s", exc)

    return None


# ── Merge OCR + VLM ───────────────────────────────────────────

def _merge_ocr_vlm(ocr_text: str, ocr_quality: float, vlm_result: dict) -> UnifiedResult:
    vlm_extraction = vlm_result.get("extraction", {})
    vlm_markdown = vlm_result.get("markdown", "")
    vlm_confidence = vlm_result.get("confidence", 0.0)

    # VLM extraction is primary (semantic understanding)
    # OCR text is backup (exact characters, positions)
    extraction = dict(vlm_extraction)

    # Use VLM markdown if available, else OCR text
    best_text = vlm_markdown if vlm_markdown else ocr_text
    best_markdown = vlm_markdown if vlm_markdown else ocr_text

    # Final confidence: weighted combination
    # VLM weight higher because it understands structure
    if vlm_confidence > 0 and ocr_quality > 0:
        final_conf = vlm_confidence * 0.7 + ocr_quality * 0.3
    elif vlm_confidence > 0:
        final_conf = vlm_confidence
    else:
        final_conf = ocr_quality

    method = "ocr+vlm_merged"
    if not ocr_text:
        method = "vlm_only"
    elif not vlm_extraction:
        method = "ocr_only"

    return UnifiedResult(
        text=best_text,
        markdown=best_markdown,
        extraction=extraction,
        tables=vlm_result.get("tables", []),
        method=method,
        ocr_text=ocr_text,
        ocr_confidence=ocr_quality,
        vlm_extraction=vlm_extraction,
        vlm_markdown=vlm_markdown,
        vlm_confidence=vlm_confidence,
        final_confidence=round(final_conf, 4),
        cost_usd=vlm_result.get("cost_usd", 0),
        quality_scores={
            "ocr_quality": ocr_quality,
            "vlm_confidence": vlm_confidence,
            "final": round(final_conf, 4),
        },
    )
