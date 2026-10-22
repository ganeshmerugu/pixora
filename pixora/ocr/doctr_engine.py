from __future__ import annotations
import asyncio
import io
import logging
import uuid
from PIL import Image
import numpy as np
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

_doctr_model: object | None = None


def _load_doctr():
    global _doctr_model
    if _doctr_model is None:
        logger.info("doctr: loading model...")
        from doctr.models import ocr_predictor
        _doctr_model = ocr_predictor(det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True)
        logger.info("doctr: model loaded")
    return _doctr_model


class DocTREngine(OCREngine):
    engine_name = "doctr"

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

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
            logger.error("doctr: recognition timed out")
            return []
        except Exception as exc:
            logger.error("doctr: recognition failed: %s", exc)
            return []

    def _recognize_sync(self, image_bytes: bytes, page_number: int) -> list[RecognizedRegion]:
        from doctr.io import DocumentFile

        model = _load_doctr()
        doc = DocumentFile.from_images([image_bytes])
        result = model(doc)

        words: list[RecognizedWord] = []
        text_parts: list[str] = []
        confidences: list[float] = []

        for page in result.pages:
            h, w = page.dimensions
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        text = word.value.strip()
                        if not text:
                            continue
                        conf = float(word.confidence)
                        geo = word.geometry
                        x1, y1 = geo[0]
                        x2, y2 = geo[1]

                        words.append(RecognizedWord(
                            text=text,
                            confidence=conf,
                            bbox=BoundingBox(
                                x=round(x1 * w), y=round(y1 * h),
                                width=round((x2 - x1) * w),
                                height=round((y2 - y1) * h),
                                page=page_number,
                            ),
                        ))
                        text_parts.append(text)
                        confidences.append(conf)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return [RecognizedRegion(
            region_id=f"doctr_{page_number}_{uuid.uuid4().hex[:8]}",
            text=" ".join(text_parts),
            confidence=avg_conf,
            words=words,
            engine="doctr",
        )]
