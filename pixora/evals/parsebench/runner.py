"""ParseBench runner — evaluates Pixora's OCR pipeline against ParseBench."""
from __future__ import annotations
import io
import logging
import os
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

    # ── Resolve file path ─────────────────────────────────────

    def _resolve_path(self, pdf_path: str) -> str:
        if os.path.exists(pdf_path):
            return pdf_path
        for base in [os.path.join(os.getcwd(), "data"), "data"]:
            candidate = os.path.join(base, pdf_path.replace("/", os.sep))
            if os.path.exists(candidate):
                return candidate
        return ""

    # ── Main parse function ───────────────────────────────────

    async def _default_parse(self, pdf_path: str) -> str:
        resolved = self._resolve_path(pdf_path)
        if not resolved:
            return ""

        ext = os.path.splitext(resolved)[1].lower()
        if ext == ".pdf":
            return await self._parse_pdf(resolved)
        if ext in (".png", ".jpg", ".jpeg"):
            return await self._ocr_image(resolved)
        return ""

    async def _parse_pdf(self, path: str) -> str:
        with open(path, "rb") as f:
            data = f.read()

        # 1. Docling — best markdown quality
        text = self._try_docling(data, path)
        if text:
            return text

        # 2. PyMuPDF font-aware markdown (bold/italic/headings)
        text = self._try_pymupdf_markdown(data)
        if text:
            return text

        # 3. pdfplumber layout-aware
        text = await self._try_pdfplumber(data, path)
        if text:
            return text

        # 4. EasyOCR for scanned PDFs
        text = await self._try_easyocr_pdf(data)
        if text:
            return text

        return ""

    # ── Strategy 1: Docling ───────────────────────────────────

    def _try_docling(self, data: bytes, path: str) -> str:
        try:
            from pixora.extraction.docling_engine import extract_with_docling
            result = extract_with_docling(data, os.path.basename(path))
            return result.get("markdown", "")
        except Exception as exc:
            logger.debug("docling failed: %s", exc)
            return ""

    # ── Strategy 2: PyMuPDF with font-aware markdown ──────────

    def _try_pymupdf_markdown(self, data: bytes) -> str:
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            pages: list[str] = []
            for pg in doc:
                md = self._page_to_markdown(pg)
                if md.strip():
                    pages.append(md)
            doc.close()
            return "\n\n".join(pages)
        except Exception as exc:
            logger.debug("pymupdf markdown failed: %s", exc)
            return ""

    def _page_to_markdown(self, page) -> str:
        blocks = page.get_text("dict", sort=True).get("blocks", [])
        lines: list[str] = []

        all_sizes: list[float] = []
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        all_sizes.append(span.get("size", 12))
        body_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 12.0

        for block in blocks:
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
                    bold = bool(flags & (1 << 4))
                    italic = bool(flags & (1 << 1))
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

                if line_max_size >= body_size * 2.0:
                    full = f"# {clean}"
                elif line_max_size >= body_size * 1.5:
                    full = f"## {clean}"
                elif line_max_size >= body_size * 1.2 and line_all_bold:
                    full = f"### {clean}"
                elif line_all_bold and len(clean) < 80 and clean == clean.upper() and any(c.isalpha() for c in clean):
                    full = f"### {clean}"

                lines.append(full)

        return "\n".join(lines)

    # ── Strategy 3: pdfplumber ────────────────────────────────

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

    # ── Strategy 4: EasyOCR for scanned PDFs ──────────────────

    async def _try_easyocr_pdf(self, data: bytes) -> str:
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(data, dpi=200)
        except Exception as exc:
            logger.debug("pdf2image failed: %s", exc)
            return ""

        all_text: list[str] = []
        for img in images:
            text = await self._ocr_pil_image(img)
            if text:
                all_text.append(text)
        return "\n\n".join(all_text)

    async def _ocr_image(self, path: str) -> str:
        try:
            from PIL import Image
            img = Image.open(path).convert("RGB")
            return await self._ocr_pil_image(img)
        except Exception as exc:
            logger.debug("image OCR failed: %s", exc)
            return ""

    async def _ocr_pil_image(self, img) -> str:
        try:
            from pixora.ocr.easyocr_engine import EasyOCREngine
            engine = EasyOCREngine()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            regions = await engine.recognize(buf.getvalue())
            return " ".join(r.get("text", "") for r in regions if r.get("text", "").strip())
        except Exception as exc:
            logger.debug("easyocr failed: %s", exc)
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
