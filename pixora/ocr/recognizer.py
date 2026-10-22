from __future__ import annotations
import logging
from pixora.ocr.engine import OCREngine, RecognizedRegion
from pixora.ocr.ensemble import OCREnsemble
from pixora.ocr.postprocessor import OCRPostProcessor, PostProcessedRegion

logger = logging.getLogger(__name__)

FALLBACK_ORDER = ["tesseract", "easyocr"]


class TextRecognizer:
    def __init__(
        self,
        engines: dict[str, OCREngine] | None = None,
        ensemble: OCREnsemble | None = None,
        postprocessor: OCRPostProcessor | None = None,
    ):
        self.engines = engines or {}
        self.ensemble = ensemble
        self.postprocessor = postprocessor or OCRPostProcessor()

    async def recognize(
        self,
        image_bytes: bytes,
        strategy: str,
        languages: list[str] | None = None,
        page_number: int = 1,
        doc_type: str = "",
        region_type: str = "TEXT",
    ) -> list[PostProcessedRegion]:
        regions = await self._execute_strategy(
            image_bytes, strategy, languages, page_number, region_type,
        )
        return self.postprocessor.process(regions, doc_type=doc_type)

    async def _execute_strategy(
        self,
        image_bytes: bytes,
        strategy: str,
        languages: list[str] | None,
        page_number: int,
        region_type: str,
    ) -> list[RecognizedRegion]:
        if strategy == "TEXT_DIRECT":
            return []

        if strategy == "TESSERACT_ONLY":
            return await self._run_engine("tesseract", image_bytes, languages, page_number)

        if strategy == "CLAUDE_VISION_PRIMARY":
            return await self._run_engine_with_fallback(
                "claude_vision", image_bytes, languages, page_number,
            )

        if strategy == "SURYA_PRIMARY":
            return await self._run_engine_with_fallback(
                "surya", image_bytes, languages, page_number,
            )

        if strategy == "DOCTR_PRIMARY":
            return await self._run_engine_with_fallback(
                "doctr", image_bytes, languages, page_number,
            )

        if strategy == "VLM_PRIMARY":
            return await self._run_engine_with_fallback(
                "got_ocr", image_bytes, languages, page_number,
                fallback_to=["claude_vision", "surya", "tesseract"],
            )

        if strategy == "GOT_OCR_PRIMARY":
            return await self._run_engine_with_fallback(
                "got_ocr", image_bytes, languages, page_number,
            )

        if strategy == "ENSEMBLE":
            if self.ensemble:
                try:
                    return await self.ensemble.recognize(
                        image_bytes, languages, page_number, region_type,
                    )
                except Exception as exc:
                    logger.warning("recognizer: ensemble failed (%s), falling back", exc)

            return await self._fallback_chain(image_bytes, languages, page_number)

        raise ValueError(f"Unknown OCR strategy: {strategy}")

    async def _run_engine(
        self,
        engine_name: str,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
    ) -> list[RecognizedRegion]:
        engine = self.engines.get(engine_name)
        if not engine:
            raise KeyError(f"Engine '{engine_name}' not registered")
        return await engine.recognize(image_bytes, languages, page_number)

    async def _run_engine_with_fallback(
        self,
        primary: str,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
        fallback_to: list[str] | None = None,
    ) -> list[RecognizedRegion]:
        engine = self.engines.get(primary)
        if engine:
            try:
                result = await engine.recognize(image_bytes, languages, page_number)
                if result and result[0].get("text", "").strip():
                    return result
                logger.warning("recognizer: %s returned empty, falling back", primary)
            except Exception as exc:
                logger.warning("recognizer: %s failed (%s), falling back", primary, exc)

        chain = fallback_to or FALLBACK_ORDER
        return await self._fallback_chain(image_bytes, languages, page_number, chain)

    async def _fallback_chain(
        self,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
        chain: list[str] | None = None,
    ) -> list[RecognizedRegion]:
        for name in (chain or FALLBACK_ORDER):
            engine = self.engines.get(name)
            if not engine:
                continue
            try:
                result = await engine.recognize(image_bytes, languages, page_number)
                if result:
                    logger.info("recognizer: fallback to '%s' succeeded", name)
                    return result
            except Exception as exc:
                logger.warning("recognizer: fallback '%s' failed: %s", name, exc)

        logger.error("recognizer: all engines failed")
        return []
