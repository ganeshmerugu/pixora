from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.ocr.engine import RecognizedRegion, RecognizedWord


class OCRDisagreement(TypedDict, total=False):
    region_id: Required[str]
    page: int
    engine_outputs: dict[str, str]
    engine_confidences: dict[str, float]
    selected_engine: str
    selection_reason: str
    was_corrected_by_human: bool | None


CONFIDENCE_GAP_THRESHOLD = 0.15


class OCRConfidenceArbiter:
    def __init__(self, region_type_preferences: dict[str, str] | None = None):
        self.region_type_preferences = region_type_preferences or {
            "HANDWRITING": "claude_vision",
            "TABLE": "tesseract",
        }
        self._disagreements: list[OCRDisagreement] = []

    def merge(
        self,
        engine_results: dict[str, list[RecognizedRegion]],
        region_type: str = "TEXT",
    ) -> list[RecognizedRegion]:
        engines = list(engine_results.keys())
        if len(engines) == 0:
            return []
        if len(engines) == 1:
            return engine_results[engines[0]]

        all_regions = []
        max_len = max(len(v) for v in engine_results.values())

        for i in range(max_len):
            candidates: dict[str, RecognizedRegion] = {}
            for eng in engines:
                regions = engine_results[eng]
                if i < len(regions):
                    candidates[eng] = regions[i]

            if not candidates:
                continue

            texts = {eng: r["text"] for eng, r in candidates.items()}
            confidences = {eng: r["confidence"] for eng, r in candidates.items()}

            if len(set(texts.values())) == 1:
                best_eng = max(confidences, key=confidences.get)  # type: ignore[arg-type]
                selected = candidates[best_eng]
                reason = "all_engines_agree"
            elif region_type in self.region_type_preferences:
                preferred = self.region_type_preferences[region_type]
                if preferred in candidates:
                    selected = candidates[preferred]
                    best_eng = preferred
                    reason = f"region_type_preference_{region_type}"
                else:
                    best_eng = max(confidences, key=confidences.get)  # type: ignore[arg-type]
                    selected = candidates[best_eng]
                    reason = "highest_confidence_fallback"
            else:
                sorted_engines = sorted(confidences.keys(), key=lambda e: confidences[e], reverse=True)
                top_eng = sorted_engines[0]
                second_eng = sorted_engines[1] if len(sorted_engines) > 1 else None

                if second_eng and (confidences[top_eng] - confidences[second_eng]) >= CONFIDENCE_GAP_THRESHOLD:
                    best_eng = top_eng
                    selected = candidates[top_eng]
                    reason = "confidence_gap"
                else:
                    best_eng = top_eng
                    selected = candidates[top_eng]
                    reason = "highest_confidence"

            self._disagreements.append(OCRDisagreement(
                region_id=selected["region_id"],
                engine_outputs=texts,
                engine_confidences=confidences,
                selected_engine=best_eng,
                selection_reason=reason,
            ))

            all_regions.append(selected)

        return all_regions

    def get_disagreements(self) -> list[OCRDisagreement]:
        return list(self._disagreements)

    def clear_disagreements(self) -> None:
        self._disagreements.clear()
