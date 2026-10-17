from __future__ import annotations
from typing import Optional
from pixora.classifiers.rules import RuleBasedClassifier
from pixora.classifiers.vision import VisionClassifier
from pixora.models.pipeline import DocumentProfile


CONFIDENCE_THRESHOLD_SKIP_VISION = 0.80


class HybridClassifier:
    def __init__(self, vision_classifier: Optional[VisionClassifier] = None):
        self.rules = RuleBasedClassifier()
        self.vision = vision_classifier

    async def classify(
        self,
        filename: str,
        first_page_text: str,
        raw_bytes: bytes | None = None,
        categories: list[dict[str, str]] | None = None,
    ) -> DocumentProfile:
        profile = self.rules.classify_by_rules(filename, first_page_text)

        if profile["confidence"] >= CONFIDENCE_THRESHOLD_SKIP_VISION:
            return profile

        if self.vision and raw_bytes and categories:
            vision_profile = await self.vision.classify(raw_bytes, categories)
            if vision_profile["confidence"] > profile["confidence"]:
                vision_profile["metadata"] = {
                    **(vision_profile.get("metadata") or {}),
                    "rule_doc_type": profile["doc_type"],
                    "rule_confidence": profile["confidence"],
                    "is_scanned": profile.get("is_scanned", False),
                    "has_tables": profile.get("has_tables", False),
                }
                vision_profile["is_scanned"] = profile.get("is_scanned", False)
                vision_profile["has_tables"] = profile.get("has_tables", False)
                vision_profile["has_handwriting"] = profile.get("has_handwriting", False)
                vision_profile["complexity"] = profile.get("complexity", 0.5)
                return vision_profile

        return profile
