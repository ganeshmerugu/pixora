from __future__ import annotations
import asyncio
import io
import logging
import uuid
from PIL import Image
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

_got_model: dict[str, object] = {}

GOT_MODEL_ID = "stepfun-ai/GOT-OCR-2.0-hf"


def _load_got():
    if "model" not in _got_model:
        logger.info("got_ocr: loading GOT-OCR2 model...")
        from transformers import AutoModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(GOT_MODEL_ID, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            GOT_MODEL_ID,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype="auto",
        )
        _got_model["model"] = model
        _got_model["tokenizer"] = tokenizer
        logger.info("got_ocr: model loaded")
    return _got_model["model"], _got_model["tokenizer"]


class GOTOCREngine(OCREngine):
    engine_name = "got_ocr"

    def __init__(self, timeout: float = 90.0, ocr_type: str = "ocr"):
        self.timeout = timeout
        self.ocr_type = ocr_type

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        if not image_bytes:
            return []

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._recognize_sync, image_bytes, page_number),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error("got_ocr: recognition timed out")
            return []
        except Exception as exc:
            logger.error("got_ocr: recognition failed: %s", exc)
            return []

    def _recognize_sync(self, image_bytes: bytes, page_number: int) -> list[RecognizedRegion]:
        import tempfile
        import os

        model, tokenizer = _load_got()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp, format="PNG")
            tmp_path = tmp.name

        try:
            result = model.chat(tokenizer, tmp_path, ocr_type=self.ocr_type)
        finally:
            os.unlink(tmp_path)

        text = result.strip() if isinstance(result, str) else str(result).strip()

        return [RecognizedRegion(
            region_id=f"got_{page_number}_{uuid.uuid4().hex[:8]}",
            text=text,
            confidence=0.9,
            words=[],
            engine="got_ocr",
            metadata={"ocr_type": self.ocr_type},
        )]
