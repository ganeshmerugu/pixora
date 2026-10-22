from __future__ import annotations
from typing import Any
from typing_extensions import Required, TypedDict
from pixora.ocr.segmenter import SegmentedRegion


class FeatureSet(TypedDict, total=False):
    mode: Required[str]
    features: dict[str, Any]
    metadata: dict[str, Any]


class FeatureExtractor:
    def extract(self, region: SegmentedRegion, mode: str = "engine_internal") -> FeatureSet:
        if mode == "classical":
            return self._extract_classical(region)
        elif mode == "deep":
            return self._extract_deep(region)
        return FeatureSet(mode="engine_internal")

    def _extract_classical(self, region: SegmentedRegion) -> FeatureSet:
        return FeatureSet(
            mode="classical",
            features={"type": "hog_zoning", "region_type": region["type"]},
        )

    def _extract_deep(self, region: SegmentedRegion) -> FeatureSet:
        return FeatureSet(
            mode="deep",
            features={"type": "cnn_feature_map", "region_type": region["type"]},
        )
