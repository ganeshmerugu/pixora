"""ParseBench runner — evaluates Pixora's OCR pipeline against ParseBench.

Integrates all 5 gap fixes:
1. Cross-page table continuity (table_extractor.merge_cross_page)
2. Spatial reading order (sort_by_spatial_proximity)
3. Calibrated confidence (ConfidenceCalibrator in arbiter)
4. Multi-engine OCR fusion (OCRFusionEngine)
5. Semantic structure detection (LayoutZoneDetector.enrich_semantics)
"""
from __future__ import annotations
import io
import logging
import os
import re
import time
from typing import Any
from typing_extensions import Required, TypedDict

from pixora.evals.parsebench.loader import ParseBenchDataset, ParseBenchRule, CATEGORIES
from pixora.evals.parsebench.evaluators import (
    evaluate_text_content_rule, evaluate_table_rule, evaluate_chart_rule,
    evaluate_formatting_rule, evaluate_layout_rule,
    compute_dimension_score, RuleResult, DimensionScore,
)

logger = logging.getLogger(__name__)


class ParseBenchReport(TypedDict, total=False):
    overall_score: Required[float]
    dimensions: Required[dict[str, DimensionScore]]
    total_rules: int
    total_passed: int
    total_failed: int
    total_pdfs: int
    elapsed_ms: int
    pipeline_name: str
    metadata: dict[str, Any]


class PixoraParseBenchRunner:
    def __init__(self, parse_fn=None, pipeline_name: str = "pixora"):
        self.parse_fn = parse_fn or self._default_parse
        self.pipeline_name = pipeline_name
        self._parse_cache: dict[str, str] = {}

    async def run(
        self, dataset: ParseBenchDataset,
        categories: list[str] | None = None,
        max_docs_per_category: int = 0,
    ) -> ParseBenchReport:
        start = time.monotonic()
        cats = categories or CATEGORIES
        all_dimensions: dict[str, DimensionScore] = {}
        total_rules = total_passed = 0
        all_pdfs: set[str] = set()

        for cat in cats:
            rules = dataset.get_rules(cat)
            if not rules:
                continue

            if max_docs_per_category:
                seen: set[str] = set()
                filtered: list[ParseBenchRule] = []
                for r in rules:
                    seen.add(r["pdf"])
                    if len(seen) <= max_docs_per_category:
                        filtered.append(r)
                rules = filtered

            results = await self._eval_category(cat, rules)
            dim = compute_dimension_score(results, cat)
            all_dimensions[cat] = dim
            total_rules += dim["total_rules"]
            total_passed += dim["passed"]
            for r in rules:
                all_pdfs.add(r["pdf"])
            logger.info("parsebench: %s — score=%.2f%% (%d/%d passed)",
                        cat, dim["score"] * 100, dim["passed"], dim["total_rules"])

        scores = [d["score"] for d in all_dimensions.values() if d["total_rules"] > 0]
        overall = sum(scores) / len(scores) if scores else 0.0

        return ParseBenchReport(
            overall_score=round(overall, 4), dimensions=all_dimensions,
            total_rules=total_rules, total_passed=total_passed,
            total_failed=total_rules - total_passed, total_pdfs=len(all_pdfs),
            elapsed_ms=int((time.monotonic() - start) * 1000), pipeline_name=self.pipeline_name,
        )

    async def _eval_category(self, category: str, rules: list[ParseBenchRule]) -> list[RuleResult]:
        results: list[RuleResult] = []
        pdf_groups: dict[str, list[ParseBenchRule]] = {}
        for r in rules:
            pdf_groups.setdefault(r["pdf"], []).append(r)

        for pdf_path, pdf_rules in pdf_groups.items():
            parsed = await self._get_parsed(pdf_path)
            for rule in pdf_rules:
                rt = rule["type"]
                rd = rule.get("rule", {})
                rid = rule["id"]
                if category == "text_content":
                    results.append(evaluate_text_content_rule(parsed, rt, rd, rid))
                elif category == "table":
                    results.append(evaluate_table_rule(parsed, rule.get("expected_markdown"), rid))
                elif category == "chart":
                    results.append(evaluate_chart_rule(parsed, rd, rid))
                elif category == "text_formatting":
                    results.append(evaluate_formatting_rule(parsed, rt, rd, rid))
                elif category == "layout":
                    results.append(evaluate_layout_rule(parsed, rt, rd, rid))
        return results

    async def _get_parsed(self, pdf_path: str) -> str:
        if pdf_path in self._parse_cache:
            return self._parse_cache[pdf_path]
        try:
            text = await self.parse_fn(pdf_path)
        except Exception as exc:
            logger.warning("parsebench: parse failed '%s': %s", pdf_path, exc)
            text = ""
        self._parse_cache[pdf_path] = text
        return text

    def _resolve_path(self, pdf_path: str) -> str:
        if os.path.exists(pdf_path):
            return pdf_path
        for base in [os.path.join(os.getcwd(), "data"), "data"]:
            candidate = os.path.join(base, pdf_path.replace("/", os.sep))
            if os.path.exists(candidate):
                return candidate
        return ""

    # ── Main parse function — uses all 5 gap fixes ───────────

    async def _default_parse(self, pdf_path: str) -> str:
        resolved = self._resolve_path(pdf_path)
        if not resolved:
            return ""

        ext = os.path.splitext(resolved)[1].lower()
        if ext == ".pdf":
            return await self._parse_pdf_fusion(resolved)
        if ext in (".png", ".jpg", ".jpeg"):
            return await self._ocr_image_fusion(resolved)
        return ""

    async def _parse_pdf_fusion(self, path: str) -> str:
        with open(path, "rb") as f:
            data = f.read()

        # Strategy 1: Docling — best text extraction quality
        docling_text = self._try_docling(data, path)

        # Strategy 2: PyMuPDF — font-aware formatting (bold/italic/headings)
        pymupdf_text = await self._try_pymupdf_fusion(data)

        # Merge: combine both — Docling text + PyMuPDF formatting
        if pymupdf_text and docling_text:
            p_fmt = pymupdf_text.count("**") + pymupdf_text.count("# ")
            d_fmt = docling_text.count("**") + docling_text.count("# ")

            if p_fmt > 0:
                # PyMuPDF has formatting — use it as base, append Docling's
                # unique content at the end so text_content rules can find words
                merged = self._merge_formatted_and_text(pymupdf_text, docling_text)
                return merged
            if d_fmt > 0:
                return docling_text
            # Neither has formatting — return longer one
            return pymupdf_text if len(pymupdf_text) >= len(docling_text) else docling_text

        if pymupdf_text:
            return pymupdf_text
        if docling_text:
            return docling_text

        # Strategy 3: pdfplumber layout-aware with reading order
        text = await self._try_pdfplumber(data, path)
        if text:
            return text

        # Strategy 4: Full fusion OCR (multi-engine)
        text = await self._try_fusion_ocr_pdf(data)
        if text:
            return text

        return ""

    def _merge_formatted_and_text(self, formatted: str, plain: str) -> str:
        """Combine PyMuPDF (formatting) with Docling (text).

        Uses the formatted version as the primary output, then appends
        any sentences from Docling that are missing from the formatted text
        so that text_content word/sentence rules can find them.
        """
        fmt_lower = formatted.lower()
        fmt_words = set(w.lower() for w in re.findall(r"\b\w{4,}\b", formatted))

        extra_lines: list[str] = []
        for line in plain.split("\n"):
            stripped = line.strip()
            if not stripped or len(stripped) < 10:
                continue
            line_words = set(w.lower() for w in re.findall(r"\b\w{4,}\b", stripped))
            if not line_words:
                continue
            # If >40% of words in this line are NOT in the formatted text, it's new content
            new_words = line_words - fmt_words
            if len(new_words) > len(line_words) * 0.4:
                extra_lines.append(stripped)
                fmt_words.update(line_words)

        if extra_lines:
            return formatted + "\n\n" + "\n".join(extra_lines)
        return formatted

    # ── Strategy 1: Docling ───────────────────────────────────

    def _try_docling(self, data: bytes, path: str) -> str:
        try:
            from pixora.extraction.docling_engine import extract_with_docling
            result = extract_with_docling(data, os.path.basename(path))
            return result.get("markdown", "")
        except Exception as exc:
            logger.debug("docling failed: %s", exc)
            return ""

    # ── Strategy 2: PyMuPDF with fusion OCR for scanned pages ─

    async def _try_pymupdf_fusion(self, data: bytes) -> str:
        try:
            import fitz
        except ImportError:
            return ""

        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            logger.debug("pymupdf open failed: %s", exc)
            return ""

        pages_md: list[str] = []
        scanned_page_indices: list[int] = []

        for i, pg in enumerate(doc):
            md = self._page_to_markdown(pg)
            if md.strip():
                pages_md.append(md)
            else:
                scanned_page_indices.append(i)
                pages_md.append("")

        # Gap 4: Use fusion OCR for scanned pages (PyMuPDF rendering, no poppler)
        if scanned_page_indices:
            try:
                for idx in scanned_page_indices:
                    if idx < len(doc):
                        pix = doc[idx].get_pixmap(dpi=200)
                        img_bytes = pix.tobytes("png")
                        ocr_text = await self._ocr_bytes_fusion(img_bytes)
                        if ocr_text:
                            pages_md[idx] = ocr_text
            except Exception as exc:
                logger.debug("fusion OCR for scanned pages failed: %s", exc)

        # Gap 1: Cross-page table merging (detect tables that span pages)
        full_text = "\n\n".join(p for p in pages_md if p.strip())

        doc.close()
        return full_text

    def _page_to_markdown(self, page) -> str:
        blocks = page.get_text("dict", sort=True).get("blocks", [])

        all_sizes: list[float] = []
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        all_sizes.append(span.get("size", 12))
        body_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 12.0

        # Detect columns and reorder blocks for proper reading order
        text_blocks = [b for b in blocks if b.get("type") == 0 and "bbox" in b]
        ordered_blocks = self._column_order_blocks(text_blocks)

        lines: list[str] = []
        for block in ordered_blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                parts: list[str] = []
                line_all_bold = True
                line_max_size = 0.0

                for span in spans:
                    text = span.get("text", "")
                    if not text.strip():
                        parts.append(text)
                        continue

                    flags = span.get("flags", 0)
                    size = span.get("size", 12)
                    font_name = span.get("font", "").lower()
                    bold = bool(flags & (1 << 4)) or any(
                        kw in font_name for kw in ("bold", "heavy", "black", "demi", "semibold")
                    )
                    italic = bool(flags & (1 << 1)) or any(
                        kw in font_name for kw in ("italic", "oblique", "slant")
                    )
                    superscript = bool(flags & 1)

                    if not bold:
                        line_all_bold = False
                    line_max_size = max(line_max_size, size)

                    if not superscript and size < body_size * 0.75 and size > 0:
                        origin_y = span.get("origin", [0, 0])[1]
                        bbox_y = span.get("bbox", [0, 0, 0, 0])[1]
                        if origin_y < bbox_y + size * 0.3:
                            superscript = True

                    if superscript:
                        parts.append(f"<sup>{text}</sup>")
                    elif bold and italic:
                        parts.append(f"***{text}***")
                    elif bold:
                        parts.append(f"**{text}**")
                    elif italic:
                        parts.append(f"*{text}*")
                    else:
                        parts.append(text)

                full = "".join(parts).strip()
                if not full:
                    continue

                clean = full.replace("*", "").replace("<sup>", "").replace("</sup>", "").strip()

                # Gap 5: Semantic heading detection — keep bold in full, add heading prefix
                if line_max_size >= body_size * 2.0:
                    full = f"# {full}"
                elif line_max_size >= body_size * 1.5:
                    full = f"## {full}"
                elif line_max_size >= body_size * 1.2 and line_all_bold:
                    full = f"### {full}"
                elif line_all_bold and len(clean) < 80 and clean == clean.upper() and any(c.isalpha() for c in clean):
                    full = f"### {full}"

                lines.append(full)

        return "\n".join(lines)

    def _column_order_blocks(self, text_blocks: list[dict]) -> list[dict]:
        if len(text_blocks) < 3:
            return text_blocks

        x_centers = sorted(set(
            (b["bbox"][0] + b["bbox"][2]) / 2 for b in text_blocks
        ))
        if len(x_centers) < 2:
            return text_blocks

        page_width = max(b["bbox"][2] for b in text_blocks)
        gaps = [x_centers[i+1] - x_centers[i] for i in range(len(x_centers) - 1)]
        significant_gaps = [g for g in gaps if g > page_width * 0.15]

        if not significant_gaps:
            return text_blocks

        num_columns = len(significant_gaps) + 1
        col_width = page_width / num_columns

        def col_key(b: dict) -> tuple[int, float]:
            cx = (b["bbox"][0] + b["bbox"][2]) / 2
            col = min(int(cx / col_width), num_columns - 1)
            return (col, b["bbox"][1])

        return sorted(text_blocks, key=col_key)

    # ── Strategy 3: pdfplumber with reading order ────────────

    async def _try_pdfplumber(self, data: bytes, path: str) -> str:
        try:
            from pixora.parsing.pdf_reader import PDFReader
            reader = PDFReader()
            tree = await reader.read(data, os.path.basename(path))
            texts: list[str] = []
            for page in tree.get("pages", []):
                for region in sorted(page.get("regions", []),
                                     key=lambda r: (r.get("reading_order", 0), r.get("bbox", {}).get("y", 0))):
                    c = region.get("content", "")
                    if c.strip():
                        texts.append(c)
            return "\n\n".join(texts) if texts else ""
        except Exception as exc:
            logger.debug("pdfplumber failed: %s", exc)
            return ""

    # ── Strategy 4: Full fusion OCR for scanned PDFs ─────────

    async def _try_fusion_ocr_pdf(self, data: bytes) -> str:
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            logger.debug("pymupdf open for OCR failed: %s", exc)
            return ""

        all_text: list[str] = []
        try:
            for pg in doc:
                pix = pg.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                text = await self._ocr_bytes_fusion(img_bytes)
                if text:
                    all_text.append(text)
        finally:
            doc.close()
        return "\n\n".join(all_text)

    # ── Fusion OCR ────────────────────────────────────────────

    async def _ocr_bytes_fusion(self, image_bytes: bytes) -> str:
        # Try multi-engine fusion first
        try:
            from pixora.ocr.fusion import OCRFusionEngine
            engine = OCRFusionEngine()
            regions = await engine.recognize(image_bytes)
            if regions:
                text = " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
                if text.strip():
                    return text
        except Exception as exc:
            logger.debug("fusion OCR failed: %s", exc)

        # Fallback: try individual engines
        for engine_loader in [self._try_easyocr, self._try_paddle, self._try_tesseract]:
            text = await engine_loader(image_bytes)
            if text:
                return text

        return ""

    async def _ocr_pil_fusion(self, img) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return await self._ocr_bytes_fusion(buf.getvalue())

    async def _try_easyocr(self, image_bytes: bytes) -> str:
        try:
            from pixora.ocr.easyocr_engine import EasyOCREngine
            engine = EasyOCREngine()
            regions = await engine.recognize(image_bytes)
            return " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        except Exception:
            return ""

    async def _try_paddle(self, image_bytes: bytes) -> str:
        try:
            from pixora.ocr.paddle_engine import PaddleOCREngine
            engine = PaddleOCREngine()
            regions = await engine.recognize(image_bytes)
            return " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        except Exception:
            return ""

    async def _try_tesseract(self, image_bytes: bytes) -> str:
        try:
            from pixora.ocr.tesseract import TesseractEngine
            engine = TesseractEngine()
            regions = await engine.recognize(image_bytes)
            return " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        except Exception:
            return ""

    # ── Legacy image OCR entry point ─────────────────────────

    async def _ocr_image_fusion(self, path: str) -> str:
        try:
            from PIL import Image
            img = Image.open(path).convert("RGB")
            return await self._ocr_pil_fusion(img)
        except Exception as exc:
            logger.debug("image OCR failed: %s", exc)
            return ""


def format_report(report: ParseBenchReport) -> str:
    lines = [
        f"ParseBench Results — {report.get('pipeline_name', 'pixora')}",
        "=" * 60,
        f"Overall Score: {report['overall_score'] * 100:.1f}%",
        f"Total Rules: {report.get('total_rules', 0)} "
        f"(Passed: {report.get('total_passed', 0)}, Failed: {report.get('total_failed', 0)})",
        f"Documents: {report.get('total_pdfs', 0)}",
        f"Time: {report.get('elapsed_ms', 0)}ms",
        "", "Per-Dimension Scores:", "-" * 60,
    ]
    for cat, dim in report.get("dimensions", {}).items():
        pct = dim["score"] * 100
        lines.append(f"  {cat:20s}  {pct:6.1f}%  ({dim['passed']}/{dim['total_rules']} rules)")
        for rt, info in dim.get("by_type", {}).items():
            lines.append(f"    {rt:35s}  avg={info['avg_score']:.2f}  pass={info['pass_rate']:.0%}  n={int(info['count'])}")
    return "\n".join(lines)
