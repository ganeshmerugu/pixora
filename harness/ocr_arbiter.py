from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.ocr.engine import RecognizedRegion, RecognizedWord
from pixora.evals.layout_eval import compute_bbox_iou


class OCRDisagreement(TypedDict, total=False):
    region_id: Required[str]
    page: int
    engine_outputs: dict[str, str]
    engine_confidences: dict[str, float]
    selected_engine: str
    selection_reason: str
    was_corrected_by_human: bool | None


CONFIDENCE_GAP_THRESHOLD = 0.15
IOU_MATCH_THRESHOLD = 0.5

ENGINE_CALIBRATION: dict[str, tuple[float, float]] = {
    "paddleocr": (1.0, 0.0),
    "easyocr": (0.95, 0.02),
    "tesseract": (0.01, 0.0),
}


class ConfidenceCalibrator:
    def __init__(self, params: dict[str, tuple[float, float]] | None = None):
        self.params = params or dict(ENGINE_CALIBRATION)

    def calibrate(self, engine: str, raw_confidence: float) -> float:
        scale, shift = self.params.get(engine, (1.0, 0.0))
        return min(1.0, max(0.0, raw_confidence * scale + shift))


class OCRConfidenceArbiter:
    def __init__(self, region_type_preferences: dict[str, str] | None = None):
        self.region_type_preferences = region_type_preferences or {
            "HANDWRITING": "claude_vision",
            "TABLE": "tesseract",
        }
        self._disagreements: list[OCRDisagreement] = []
        self.calibrator = ConfidenceCalibrator()

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

            selected, best_eng, reason = self._select_best(candidates, region_type)
            self._record_disagreement(candidates, best_eng, reason, selected)
            all_regions.append(selected)

        return all_regions

    def merge_spatial(
        self,
        engine_results: dict[str, list[RecognizedRegion]],
        region_type: str = "TEXT",
    ) -> list[RecognizedRegion]:
        engines = list(engine_results.keys())
        if len(engines) == 0:
            return []
        if len(engines) == 1:
            return engine_results[engines[0]]

        primary = engines[0]
        primary_regions = engine_results[primary]

        merged: list[RecognizedRegion] = []
        for region in primary_regions:
            candidates: dict[str, RecognizedRegion] = {primary: region}
            r_bbox = region.get("words", [{}])[0].get("bbox") if region.get("words") else None

            for eng in engines[1:]:
                best_match = self._find_spatial_match(region, engine_results[eng], r_bbox)
                if best_match:
                    candidates[eng] = best_match

            if len(candidates) == 1:
                cal_conf = self.calibrator.calibrate(primary, region["confidence"])
                result = dict(region)
                result["confidence"] = cal_conf
                merged.append(result)  # type: ignore[arg-type]
                continue

            selected, best_eng, reason = self._select_best_calibrated(candidates, region_type)
            self._record_disagreement(candidates, best_eng, reason, selected)
            merged.append(selected)

        return merged

    def _find_spatial_match(
        self,
        target: RecognizedRegion,
        candidates: list[RecognizedRegion],
        target_bbox: dict | None,
    ) -> RecognizedRegion | None:
        if not target_bbox:
            return None

        best_iou = 0.0
        best_match = None
        for cand in candidates:
            cand_bbox = cand.get("words", [{}])[0].get("bbox") if cand.get("words") else None
            if not cand_bbox:
                continue
            iou = compute_bbox_iou(target_bbox, cand_bbox)
            if iou > best_iou and iou >= IOU_MATCH_THRESHOLD:
                best_iou = iou
                best_match = cand
        return best_match

    def _select_best(
        self,
        candidates: dict[str, RecognizedRegion],
        region_type: str,
    ) -> tuple[RecognizedRegion, str, str]:
        texts = {eng: r["text"] for eng, r in candidates.items()}
        confidences = {eng: r["confidence"] for eng, r in candidates.items()}

        if len(set(texts.values())) == 1:
            best_eng = max(confidences, key=confidences.get)  # type: ignore[arg-type]
            return candidates[best_eng], best_eng, "all_engines_agree"

        if region_type in self.region_type_preferences:
            preferred = self.region_type_preferences[region_type]
            if preferred in candidates:
                return candidates[preferred], preferred, f"region_type_preference_{region_type}"

        sorted_engines = sorted(confidences.keys(), key=lambda e: confidences[e], reverse=True)
        top_eng = sorted_engines[0]
        return candidates[top_eng], top_eng, "highest_confidence"

    def _select_best_calibrated(
        self,
        candidates: dict[str, RecognizedRegion],
        region_type: str,
    ) -> tuple[RecognizedRegion, str, str]:
        texts = {eng: r["text"] for eng, r in candidates.items()}
        cal_confs = {eng: self.calibrator.calibrate(eng, r["confidence"]) for eng, r in candidates.items()}

        text_groups: dict[str, list[str]] = {}
        for eng, text in texts.items():
            normalized = text.strip().lower()
            text_groups.setdefault(normalized, []).append(eng)

        for normalized, agreeing_engines in text_groups.items():
            if len(agreeing_engines) >= 2:
                best_eng = max(agreeing_engines, key=lambda e: cal_confs[e])
                result = dict(candidates[best_eng])
                result["confidence"] = min(1.0, cal_confs[best_eng] * 1.1)
                return result, best_eng, "text_vote_agreement"  # type: ignore[return-value]

        if region_type in self.region_type_preferences:
            preferred = self.region_type_preferences[region_type]
            if preferred in candidates:
                result = dict(candidates[preferred])
                result["confidence"] = cal_confs[preferred]
                return result, preferred, f"region_type_preference_{region_type}"  # type: ignore[return-value]

        best_eng = max(cal_confs, key=cal_confs.get)  # type: ignore[arg-type]
        result = dict(candidates[best_eng])
        result["confidence"] = cal_confs[best_eng]
        return result, best_eng, "calibrated_confidence"  # type: ignore[return-value]

    def _record_disagreement(
        self,
        candidates: dict[str, RecognizedRegion],
        best_eng: str,
        reason: str,
        selected: RecognizedRegion,
    ) -> None:
        texts = {eng: r["text"] for eng, r in candidates.items()}
        confidences = {eng: r["confidence"] for eng, r in candidates.items()}
        self._disagreements.append(OCRDisagreement(
            region_id=selected["region_id"],
            engine_outputs=texts,
            engine_confidences=confidences,
            selected_engine=best_eng,
            selection_reason=reason,
        ))

    def get_disagreements(self) -> list[OCRDisagreement]:
        return list(self._disagreements)

    def clear_disagreements(self) -> None:
        self._disagreements.clear()
