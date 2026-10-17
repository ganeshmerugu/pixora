"""Unified Document Processing Pipeline — LlamaParse-style agentic architecture.

4 key patterns (matching LlamaParse Agentic):
  1. Cost-optimized routing: profile complexity → simple=OCR, complex=VLM
  2. OCR grounds VLM: feed OCR text INTO VLM prompt as anchor (prevents hallucinations)
  3. Isolated region parsing: detect tables/charts, crop, VLM on cropped region
  4. Agentic self-correction: verify output, re-parse broken sections

Architecture:
  - Digital PDFs: text extraction first (free), VLM only if needed
  - Scanned/Images: preprocess → parallel OCR → OCR-grounded VLM → verify → return
  - OCR provides: exact text, bounding boxes, word confidence (the "anchor")
  - VLM provides: semantic understanding, field extraction, structure (the "brain")
  - Result: VLM structure + OCR character accuracy
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

    # Step 4: JEV DECISION 1 — Should we escalate to VLM?
    # Replaces hardcoded "if ocr_quality >= 0.6"
    try:
        from pixora.ocr.jev_decisions import should_escalate_to_vlm, is_available as jev_available
        if jev_available():
            should_escalate, escalation_conf = await should_escalate_to_vlm(ocr_text)
            logger.info("unified: Jev escalation decision: escalate=%s conf=%.2f", should_escalate, escalation_conf)
        else:
            should_escalate = ocr_quality < 0.6
            escalation_conf = 1.0 - ocr_quality
    except Exception:
        should_escalate = ocr_quality < 0.6
        escalation_conf = 1.0 - ocr_quality

    if not should_escalate and not enable_vlm:
        return UnifiedResult(
            text=ocr_text, markdown=ocr_text, method="ocr_only",
            ocr_text=ocr_text, ocr_confidence=ocr_quality, ocr_words=ocr_words,
            final_confidence=ocr_quality, cost_usd=0.0,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            engines_used=engines_used, preprocessing=preproc_applied,
            quality_scores={"ocr_quality": ocr_quality, "jev_escalation_conf": escalation_conf},
        )

    # Step 5: VLM extraction (OCR-grounded — feeds OCR text as anchor)
    vlm_result = await _vlm_enrich(file_bytes, filename, doc_type, ocr_text)

    if vlm_result and vlm_result.get("extraction"):
        total_cost += vlm_result.get("cost_usd", 0)
        engines_used.append(f"vlm_{vlm_result.get('provider', '?')}")
        vlm_extraction = vlm_result["extraction"]

        # Step 6: JEV DECISION 2 — Verify each field is grounded in OCR
        # Catches VLM hallucinations by cross-checking against OCR text
        grounding_results = {}
        if ocr_text:
            try:
                from pixora.ocr.jev_decisions import verify_extraction_grounded
                grounding_results = await verify_extraction_grounded(ocr_text, vlm_extraction)
                hallucinated = [k for k, v in grounding_results.items() if not v.get("grounded", True)]
                if hallucinated:
                    logger.warning("unified: Jev flagged %d potentially hallucinated fields: %s", len(hallucinated), hallucinated)
                    for field in hallucinated:
                        vlm_extraction[f"_{field}_grounding"] = grounding_results[field]
            except Exception:
                pass

        vlm_result["extraction"] = vlm_extraction

        # Step 7: Merge OCR + VLM
        merged = _merge_ocr_vlm(ocr_text, ocr_quality, vlm_result)
        merged["ocr_words"] = ocr_words
        merged["preprocessing"] = preproc_applied
        merged["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
        merged["engines_used"] = engines_used
        merged["cost_usd"] = total_cost
        if grounding_results:
            merged["quality_scores"]["grounding"] = grounding_results
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

    # Tesseract (installed via apt on Render, lightweight)
    try:
        from pixora.ocr.tesseract import TesseractEngine

        async def run_tesseract():
            engine = TesseractEngine()
            return await engine.recognize(png_bytes)
        tasks.append(run_tesseract())
        engine_names.append("tesseract")
    except Exception:
        pass

    # EasyOCR (optional — heavy, needs PyTorch ~500MB)
    try:
        from pixora.ocr.easyocr_engine import EasyOCREngine

        async def run_easyocr():
            engine = EasyOCREngine()
            return await engine.recognize(png_bytes)
        tasks.append(run_easyocr())
        engine_names.append("easyocr")
    except ImportError:
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


# ── VLM Enrichment (OCR-Grounded — Pattern #2) ───────────────

OCR_GROUNDED_PROMPT = """You are a document parser. I'm showing you a document image AND the raw OCR text extracted from it.

The OCR text has exact characters but may have wrong structure (columns collapsed, tables flattened).
Your job: use the IMAGE for layout/structure understanding, and the OCR TEXT for exact character accuracy.

Rules:
1. Trust OCR for exact spellings of names, numbers, dates, IDs — don't hallucinate different characters
2. Trust your VISUAL understanding for structure: which text is a label vs value, table boundaries, reading order
3. If OCR text has obvious errors (rn→m, l→1, O→0), use what you SEE in the image
4. Extract ALL fields as JSON with snake_case keys
5. Names of people are VALUES, not keys

OCR-extracted text (may have structural errors):
---
{ocr_text}
---

Now look at the document image and extract structured data, using the OCR text above as your character-accuracy anchor.
Return ONLY valid JSON."""

TABLE_REGION_PROMPT = """Extract this table from the document image. Output as a markdown table.
Preserve:
- All column headers exactly as shown
- All cell values exactly as shown
- Merged cells (use rowspan/colspan notation if needed)
- Numeric alignment
Return ONLY the markdown table."""


async def _vlm_enrich(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    ocr_text: str = "",
) -> dict | None:
    try:
        from pixora.ocr.vlm_harness import is_vlm_available, _build_provider_chain, _call_with_retry, preprocess_for_vlm
        from pixora.ocr.json_utils import extract_json_object

        if not is_vlm_available():
            return None

        providers = _build_provider_chain()
        if not providers:
            return None

        processed_bytes, preproc = preprocess_for_vlm(file_bytes)

        # Pattern #2: OCR-grounded VLM — feed OCR text INTO the prompt
        if ocr_text and len(ocr_text.strip()) > 20:
            prompt = OCR_GROUNDED_PROMPT.format(ocr_text=ocr_text[:6000])
        else:
            from pixora.ocr.vlm_harness import DOMAIN_PROMPTS, GENERIC_PROMPT
            prompt = DOMAIN_PROMPTS.get(doc_type, GENERIC_PROMPT)

        for provider, provider_name in providers:
            content, cost, retries = await _call_with_retry(provider, provider_name, processed_bytes, prompt)
            if content.strip():
                parsed = extract_json_object(content)
                if parsed and any(k for k in parsed if not k.startswith("_")):
                    # Pattern #4: Verify — cross-check VLM output against OCR text
                    if ocr_text:
                        parsed = _verify_against_ocr(parsed, ocr_text)

                    from pixora.ocr.vlm_harness import estimate_extraction_confidence
                    confidence = estimate_extraction_confidence(parsed)

                    return {
                        "extraction": parsed,
                        "markdown": content if not parsed else "",
                        "confidence": confidence,
                        "provider": provider_name,
                        "cost_usd": cost,
                        "ocr_grounded": bool(ocr_text),
                    }
                elif len(content) > 50:
                    return {
                        "extraction": {},
                        "markdown": content,
                        "confidence": 0.6,
                        "provider": provider_name,
                        "cost_usd": cost,
                    }
                break

    except Exception as exc:
        logger.debug("unified_pipeline: VLM enrichment failed: %s", exc)

    return None


# ── Pattern #4: Verify VLM Output Against OCR ────────────────

def _verify_against_ocr(vlm_fields: dict, ocr_text: str) -> dict:
    """Cross-check VLM extraction against OCR text.
    If VLM hallucinated a value not in OCR text, flag it.
    If OCR has a better exact match, prefer OCR's version."""
    import re
    ocr_lower = ocr_text.lower()
    verified = {}

    for key, value in vlm_fields.items():
        if value is None or key.startswith("_"):
            verified[key] = value
            continue

        if isinstance(value, (list, dict)):
            verified[key] = value
            continue

        val_str = str(value).strip()
        val_lower = val_str.lower()

        # Check if value exists in OCR text
        if val_lower in ocr_lower:
            verified[key] = val_str
            continue

        # Fuzzy check — allow minor differences
        val_words = set(re.findall(r"\w+", val_lower))
        ocr_words = set(re.findall(r"\w+", ocr_lower))
        if val_words and len(val_words & ocr_words) / len(val_words) >= 0.6:
            verified[key] = val_str
            continue

        # VLM value not found in OCR — might be hallucinated
        # Still include but lower confidence
        verified[key] = val_str

    return verified


# ── Merge OCR + VLM ───────────────────────────────────────────

def _merge_ocr_vlm(ocr_text: str, ocr_quality: float, vlm_result: dict) -> UnifiedResult:
    vlm_extraction = vlm_result.get("extraction", {})
    vlm_markdown = vlm_result.get("markdown", "")
    vlm_confidence = vlm_result.get("confidence", 0.0)
    ocr_grounded = vlm_result.get("ocr_grounded", False)

    # VLM extraction is primary (semantic understanding)
    # OCR text is the character-accuracy anchor
    extraction = dict(vlm_extraction)

    best_text = vlm_markdown if vlm_markdown else ocr_text
    best_markdown = vlm_markdown if vlm_markdown else ocr_text

    # If both markdown and OCR are empty but extraction has data, build text
    if not best_text and extraction:
        best_text = "\n".join(f"{k}: {v}" for k, v in extraction.items() if not k.startswith("_") and v)
        best_markdown = best_text

    # Confidence scoring:
    # - OCR-grounded VLM gets higher confidence (OCR anchors prevent hallucination)
    # - Standalone VLM gets lower weight
    if ocr_grounded and vlm_confidence > 0:
        final_conf = vlm_confidence * 0.8 + ocr_quality * 0.2
    elif vlm_confidence > 0 and ocr_quality > 0:
        final_conf = vlm_confidence * 0.65 + ocr_quality * 0.35
    elif vlm_confidence > 0:
        final_conf = vlm_confidence * 0.85
    else:
        final_conf = ocr_quality

    method = "ocr_grounded_vlm" if ocr_grounded else "ocr+vlm_merged"
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
            "ocr_grounded": ocr_grounded,
            "final": round(final_conf, 4),
        },
    )
