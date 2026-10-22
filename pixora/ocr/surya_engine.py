from __future__ import annotations
import asyncio
import io
import logging
import uuid
from PIL import Image
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

_surya_models: dict[str, object] = {}


def _load_surya():
    if "rec" not in _surya_models:
        logger.info("surya: loading recognition model...")
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        _surya_models["rec"] = RecognitionPredictor()
        _surya_models["det"] = DetectionPredictor()
        logger.info("surya: models loaded")
    return _surya_models["det"], _surya_models["rec"]


class SuryaEngine(OCREngine):
    engine_name = "surya"

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
                loop.run_in_executor(None, self._recognize_sync, image_bytes, languages, page_number),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error("surya: recognition timed out")
            return []
        except Exception as exc:
            logger.error("surya: recognition failed: %s", exc)
            return []

    def _recognize_sync(
        self,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
    ) -> list[RecognizedRegion]:
        from surya.recognition import run_recognition
        from surya.detection import run_detection

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        det_predictor, rec_predictor = _load_surya()

        det_results = run_detection([image], det_predictor)
        rec_results = run_recognition(
            [image], rec_predictor, det_results,
            languages=languages or ["en"],
        )

        if not rec_results or not rec_results[0].text_lines:
            return [RecognizedRegion(
                region_id=f"surya_{page_number}_{uuid.uuid4().hex[:8]}",
                text="", confidence=0.0, words=[], engine="surya",
            )]

        words: list[RecognizedWord] = []
        text_parts: list[str] = []
        confidences: list[float] = []

        for line in rec_results[0].text_lines:
            text = line.text.strip()
            if not text:
                continue
            conf = float(line.confidence)
            bbox = line.bbox
            words.append(RecognizedWord(
                text=text,
                confidence=conf,
                bbox=BoundingBox(
                    x=float(bbox[0]), y=float(bbox[1]),
                    width=float(bbox[2] - bbox[0]),
                    height=float(bbox[3] - bbox[1]),
                    page=page_number,
                ),
            ))
            text_parts.append(text)
            confidences.append(conf)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return [RecognizedRegion(
            region_id=f"surya_{page_number}_{uuid.uuid4().hex[:8]}",
            text=" ".join(text_parts),
            confidence=avg_conf,
            words=words,
            engine="surya",
        )]
