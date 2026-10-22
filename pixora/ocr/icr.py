from __future__ import annotations
import uuid
from pixora.ocr.engine import OCREngine, RecognizedRegion
from pixora.providers.base import VisionProvider


HANDWRITING_PROMPT = """Extract all handwritten text from this image. Return the text exactly as written.
If uncertain about a character, use your best judgment. Include line breaks where they appear.
Return plain text only."""


class ICREngine(OCREngine):
    engine_name = "icr_handwriting"

    def __init__(self, provider: VisionProvider):
        self.provider = provider

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        prompt = HANDWRITING_PROMPT
        if languages:
            prompt += f"\nLanguages: {', '.join(languages)}"

        resp = await self.provider.analyze_image(image_bytes, prompt)
        text = resp["content"].strip()

        return [RecognizedRegion(
            region_id=f"icr_{page_number}_{uuid.uuid4().hex[:8]}",
            text=text,
            confidence=0.7,
            words=[],
            engine="icr_handwriting",
            metadata={"tokens_used": resp.get("tokens_used", 0)},
        )]
