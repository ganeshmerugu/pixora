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

DEFAULT_TIMEOUT_S = 60

_reader_cache: dict[str, object] = {}

try:
    import easyocr as _easyocr
    _HAS_EASYOCR = True
except ImportError:
    _easyocr = None  # type: ignore[assignment]
    _HAS_EASYOCR = False


def _get_reader(languages: list[str] | None = None) -> object:
    if not _HAS_EASYOCR:
        raise ImportError("easyocr not installed")
    key = ",".join(sorted(languages or ["en"]))
    if key not in _reader_cache:
        _reader_cache[key] = _easyocr.Reader(languages or ["en"], gpu=False, verbose=False)
    return _reader_cache[key]


class EasyOCREngine(OCREngine):
    engine_name = "easyocr"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_S):
        self.timeout = timeout

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        if not _HAS_EASYOCR or not image_bytes:
            return []

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._recognize_sync, image_bytes, languages, page_number),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error("easyocr: recognition timed out after %.1fs", self.timeout)
            return []
        except Exception as exc:
            logger.error("easyocr: recognition failed: %s", exc)
            return []

    def _recognize_sync(
        self,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
    ) -> list[RecognizedRegion]:
        try:
            reader = _get_reader(languages)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(image)
        except Exception as exc:
            logger.error("easyocr: failed to prepare image: %s", exc)
            return []

        results = reader.readtext(arr)

        words: list[RecognizedWord] = []
        text_parts: list[str] = []
        confidences: list[float] = []

        for bbox_pts, text, conf in results:
            if not text.strip():
                continue

            xs = [p[0] for p in bbox_pts]
            ys = [p[1] for p in bbox_pts]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            words.append(RecognizedWord(
                text=text,
                confidence=float(conf),
                bbox=BoundingBox(
                    x=round(float(x_min)), y=round(float(y_min)),
                    width=round(float(x_max - x_min)), height=round(float(y_max - y_min)),
                    page=page_number,
                ),
            ))
            text_parts.append(text)
            confidences.append(float(conf))

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return [RecognizedRegion(
            region_id=f"easyocr_{page_number}_{uuid.uuid4().hex[:8]}",
            text=" ".join(text_parts),
            confidence=avg_conf,
            words=words,
            engine="easyocr",
        )]
