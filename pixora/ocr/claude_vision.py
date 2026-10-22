from __future__ import annotations
import json
import logging
import uuid
from typing import Any
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.ocr.json_utils import extract_json_object
from pixora.providers.base import VisionProvider
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)


STRUCTURE_PRESERVING_PROMPT = """Analyze this document image and extract ALL content with full structural understanding.

You must return a JSON object with this exact schema:
{
  "content_markdown": "Full document content in Markdown preserving headers, tables, lists, and reading order",
  "regions": [
    {
      "type": "HEADER|TEXT|TABLE|LIST|FIGURE_CAPTION|FOOTER|HANDWRITING|FORM_FIELD|SIGNATURE",
      "content": "region text content",
      "reading_order": 0,
      "confidence": 0.95,
      "bbox_pct": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.1},
      "words": [
        {"text": "word", "confidence": 0.95, "bbox_pct": {"x": 0.0, "y": 0.0, "width": 0.05, "height": 0.02}}
      ]
    }
  ],
  "layout": {
    "columns": 1,
    "has_tables": false,
    "has_headers": true,
    "has_footers": false,
    "has_handwriting": false,
    "has_images": false,
    "reading_order_confidence": 0.95
  },
  "overall_confidence": 0.95
}

Rules:
- Preserve the EXACT reading order a human would follow (left-to-right, top-to-bottom, accounting for columns)
- Render tables as Markdown tables in content_markdown
- Detect and label multi-column layouts
- bbox_pct values are percentages of page dimensions (0.0 to 1.0)
- Separate headers, footers, and body content
- Flag handwritten vs printed regions
- Include figure/chart captions as FIGURE_CAPTION regions
- Every word gets a confidence score"""


SIMPLE_TEXT_PROMPT = """Extract all text from this image with per-word bounding boxes.
Return JSON:
{
  "text": "full text content",
  "words": [{"text": "word", "confidence": 0.95, "x": 0, "y": 0, "width": 50, "height": 20}],
  "confidence": 0.95
}
Be precise. Include every word visible in the image."""


class ClaudeVisionOCR(OCREngine):
    engine_name = "claude_vision"

    def __init__(self, provider: VisionProvider, structure_mode: bool = True):
        self.provider = provider
        self.structure_mode = structure_mode

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        if self.structure_mode:
            return await self._structured_recognize(image_bytes, languages, page_number)
        return await self._simple_recognize(image_bytes, languages, page_number)

    async def recognize_structured(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
        page_width: int = 0,
        page_height: int = 0,
    ) -> StructuredVisionResult:
        prompt = STRUCTURE_PRESERVING_PROMPT
        if languages:
            prompt += f"\nLanguages present: {', '.join(languages)}"

        resp = await self.provider.analyze_image(image_bytes, prompt)
        content = resp["content"]

        parsed = extract_json_object(content)
        if not parsed:
            logger.warning("claude_vision: failed to parse structured response")
            return StructuredVisionResult(
                content_markdown=content,
                regions=[],
                layout=LayoutInfo(columns=1, reading_order_confidence=0.5),
                overall_confidence=0.6,
                tokens_used=resp.get("tokens_used", 0),
            )

        regions: list[RecognizedRegion] = []
        for i, r in enumerate(parsed.get("regions", [])):
            bbox_pct = r.get("bbox_pct", {})
            bbox = BoundingBox(
                x=bbox_pct.get("x", 0.0) * max(page_width, 1),
                y=bbox_pct.get("y", 0.0) * max(page_height, 1),
                width=bbox_pct.get("width", 0.0) * max(page_width, 1),
                height=bbox_pct.get("height", 0.0) * max(page_height, 1),
                page=page_number,
            )

            words: list[RecognizedWord] = []
            for w in r.get("words", []):
                w_bbox_pct = w.get("bbox_pct", {})
                words.append(RecognizedWord(
                    text=str(w.get("text", "")),
                    confidence=float(w.get("confidence", 0.85)),
                    bbox=BoundingBox(
                        x=w_bbox_pct.get("x", 0.0) * max(page_width, 1),
                        y=w_bbox_pct.get("y", 0.0) * max(page_height, 1),
                        width=w_bbox_pct.get("width", 0.0) * max(page_width, 1),
                        height=w_bbox_pct.get("height", 0.0) * max(page_height, 1),
                        page=page_number,
                    ),
                ))

            regions.append(RecognizedRegion(
                region_id=f"vlm_{page_number}_{i}_{uuid.uuid4().hex[:8]}",
                text=str(r.get("content", "")),
                confidence=float(r.get("confidence", 0.85)),
                words=words,
                engine="claude_vision_structured",
                metadata={
                    "region_type": r.get("type", "TEXT"),
                    "reading_order": r.get("reading_order", i),
                    "bbox": dict(bbox),
                },
            ))

        layout_data = parsed.get("layout", {})
        layout = LayoutInfo(
            columns=layout_data.get("columns", 1),
            has_tables=layout_data.get("has_tables", False),
            has_headers=layout_data.get("has_headers", False),
            has_footers=layout_data.get("has_footers", False),
            has_handwriting=layout_data.get("has_handwriting", False),
            has_images=layout_data.get("has_images", False),
            reading_order_confidence=layout_data.get("reading_order_confidence", 0.8),
        )

        return StructuredVisionResult(
            content_markdown=parsed.get("content_markdown", ""),
            regions=regions,
            layout=layout,
            overall_confidence=float(parsed.get("overall_confidence", 0.85)),
            tokens_used=resp.get("tokens_used", 0),
        )

    async def _structured_recognize(
        self, image_bytes: bytes, languages: list[str] | None, page_number: int
    ) -> list[RecognizedRegion]:
        result = await self.recognize_structured(image_bytes, languages, page_number)
        if result["regions"]:
            return result["regions"]
        return [RecognizedRegion(
            region_id=f"vlm_{page_number}_{uuid.uuid4().hex[:8]}",
            text=result["content_markdown"],
            confidence=result["overall_confidence"],
            words=[],
            engine="claude_vision_structured",
        )]

    async def _simple_recognize(
        self, image_bytes: bytes, languages: list[str] | None, page_number: int
    ) -> list[RecognizedRegion]:
        prompt = SIMPLE_TEXT_PROMPT
        if languages:
            prompt += f"\nLanguages present: {', '.join(languages)}"

        resp = await self.provider.analyze_image(image_bytes, prompt)
        content = resp["content"]

        parsed = extract_json_object(content)
        if parsed:
            text = parsed.get("text", content)
            confidence = float(parsed.get("confidence", 0.85))
            words: list[RecognizedWord] = []
            for w in parsed.get("words", []):
                words.append(RecognizedWord(
                    text=str(w.get("text", "")),
                    confidence=float(w.get("confidence", confidence)),
                    bbox=BoundingBox(
                        x=float(w.get("x", 0)), y=float(w.get("y", 0)),
                        width=float(w.get("width", 0)), height=float(w.get("height", 0)),
                        page=page_number,
                    ),
                ))
        else:
            text = content
            confidence = 0.7
            words = []

        return [RecognizedRegion(
            region_id=f"vision_{page_number}_{uuid.uuid4().hex[:8]}",
            text=text, confidence=confidence, words=words,
            engine="claude_vision",
            metadata={"tokens_used": resp.get("tokens_used", 0)},
        )]

class LayoutInfo(dict):
    def __init__(
        self,
        columns: int = 1,
        has_tables: bool = False,
        has_headers: bool = False,
        has_footers: bool = False,
        has_handwriting: bool = False,
        has_images: bool = False,
        reading_order_confidence: float = 0.8,
    ):
        super().__init__(
            columns=columns, has_tables=has_tables, has_headers=has_headers,
            has_footers=has_footers, has_handwriting=has_handwriting,
            has_images=has_images, reading_order_confidence=reading_order_confidence,
        )


class StructuredVisionResult(dict):
    def __init__(
        self,
        content_markdown: str = "",
        regions: list[RecognizedRegion] | None = None,
        layout: LayoutInfo | None = None,
        overall_confidence: float = 0.0,
        tokens_used: int = 0,
    ):
        super().__init__(
            content_markdown=content_markdown,
            regions=regions or [],
            layout=layout or LayoutInfo(),
            overall_confidence=overall_confidence,
            tokens_used=tokens_used,
        )
