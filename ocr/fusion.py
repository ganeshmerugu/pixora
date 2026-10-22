"""Multi-engine OCR fusion — runs available engines in parallel, merges spatially."""
from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Any

from pixora.ocr.engine import OCREngine, RecognizedRegion
from pixora.harness.ocr_arbiter import OCRConfidenceArbiter

logger = logging.getLogger(__name__)


def _try_load_engines() -> list[tuple[str, OCREngine]]:
    engines: list[tuple[str, OCREngine]] = []

    try:
        from pixora.ocr.paddle_engine import PaddleOCREngine
        engines.append(("paddleocr", PaddleOCREngine()))
    except Exception:
        pass

    try:
        from pixora.ocr.easyocr_engine import EasyOCREngine
        engines.append(("easyocr", EasyOCREngine()))
    except Exception:
        pass

    try:
        from pixora.ocr.tesseract import TesseractEngine
        engines.append(("tesseract", TesseractEngine()))
    except Exception:
        pass

    return engines


class OCRFusionEngine(OCREngine):
    engine_name = "fusion"

    def __init__(
        self,
        engines: list[tuple[str, OCREngine]] | None = None,
        arbiter: OCRConfidenceArbiter | None = None,
    ):
        self._engines = engines
        self._arbiter = arbiter or OCRConfidenceArbiter()

    def _get_engines(self) -> list[tuple[str, OCREngine]]:
        if self._engines is None:
            self._engines = _try_load_engines()
        return self._engines

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        engines = self._get_engines()

        if not engines:
            return []

        if len(engines) == 1:
            name, engine = engines[0]
            try:
                return await engine.recognize(image_bytes, languages, page_number)
            except Exception as exc:
                logger.warning("fusion: single engine %s failed: %s", name, exc)
                return []

        tasks = {}
        for name, engine in engines:
            tasks[name] = engine.recognize(image_bytes, languages, page_number)

        results: dict[str, list[RecognizedRegion]] = {}
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (name, _), result in zip(engines, gathered):
            if isinstance(result, Exception):
                logger.warning("fusion: engine %s failed: %s", name, result)
                continue
            if result:
                results[name] = result

        if not results:
            return []

        if len(results) == 1:
            return list(results.values())[0]

        try:
            merged = self._arbiter.merge_spatial(results)
        except Exception:
            merged = self._arbiter.merge(results)

        return merged

    def get_disagreements(self) -> list[dict]:
        return self._arbiter.get_disagreements()
