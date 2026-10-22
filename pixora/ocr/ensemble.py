from __future__ import annotations
import asyncio
import logging
import time
from pixora.ocr.engine import OCREngine, RecognizedRegion
from pixora.harness.ocr_arbiter import OCRConfidenceArbiter

logger = logging.getLogger(__name__)

DEFAULT_ENGINE_TIMEOUTS: dict[str, float] = {
    "tesseract": 30.0,
    "easyocr": 60.0,
    "claude_vision": 45.0,
    "icr_handwriting": 45.0,
}

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_RESET_S = 60.0


class _CircuitBreaker:
    def __init__(self, threshold: int = CIRCUIT_BREAKER_THRESHOLD, reset_s: float = CIRCUIT_BREAKER_RESET_S):
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._threshold = threshold
        self._reset_s = reset_s

    def is_open(self, engine_name: str) -> bool:
        if engine_name not in self._opened_at:
            return False
        elapsed = time.monotonic() - self._opened_at[engine_name]
        if elapsed >= self._reset_s:
            self._failures.pop(engine_name, None)
            self._opened_at.pop(engine_name, None)
            logger.info("circuit breaker reset for engine '%s'", engine_name)
            return False
        return True

    def record_failure(self, engine_name: str) -> None:
        self._failures[engine_name] = self._failures.get(engine_name, 0) + 1
        if self._failures[engine_name] >= self._threshold:
            self._opened_at[engine_name] = time.monotonic()
            logger.warning(
                "circuit breaker OPEN for engine '%s' after %d failures",
                engine_name, self._failures[engine_name],
            )

    def record_success(self, engine_name: str) -> None:
        self._failures.pop(engine_name, None)
        self._opened_at.pop(engine_name, None)


class OCREnsemble:
    def __init__(
        self,
        engines: list[OCREngine],
        arbiter: OCRConfidenceArbiter | None = None,
        engine_timeouts: dict[str, float] | None = None,
    ):
        self.engines = engines
        self.arbiter = arbiter or OCRConfidenceArbiter()
        self.timeouts = engine_timeouts or DEFAULT_ENGINE_TIMEOUTS
        self._breaker = _CircuitBreaker()

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
        region_type: str = "TEXT",
    ) -> list[RecognizedRegion]:
        available = [e for e in self.engines if not self._breaker.is_open(e.engine_name)]

        if not available:
            logger.error("ensemble: all engines circuit-broken, resetting and retrying")
            available = self.engines

        if len(available) == 1:
            try:
                timeout = self.timeouts.get(available[0].engine_name, 30.0)
                result = await asyncio.wait_for(
                    available[0].recognize(image_bytes, languages, page_number),
                    timeout=timeout,
                )
                self._breaker.record_success(available[0].engine_name)
                return result
            except Exception as exc:
                self._breaker.record_failure(available[0].engine_name)
                logger.error("ensemble: single engine '%s' failed: %s", available[0].engine_name, exc)
                return []

        tasks = []
        engine_order: list[OCREngine] = []
        for eng in available:
            timeout = self.timeouts.get(eng.engine_name, 30.0)
            tasks.append(asyncio.wait_for(
                eng.recognize(image_bytes, languages, page_number),
                timeout=timeout,
            ))
            engine_order.append(eng)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        engine_results: dict[str, list[RecognizedRegion]] = {}
        for eng, result in zip(engine_order, results):
            if isinstance(result, Exception):
                self._breaker.record_failure(eng.engine_name)
                logger.warning("ensemble: engine '%s' failed: %s", eng.engine_name, result)
                continue
            self._breaker.record_success(eng.engine_name)
            engine_results[eng.engine_name] = result

        if not engine_results:
            logger.error("ensemble: all engines failed")
            return []

        return self.arbiter.merge(engine_results, region_type=region_type)
