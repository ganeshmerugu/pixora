from __future__ import annotations
from pixora.providers.base import ClassificationProvider, ClassificationResult
from pixora.models.pipeline import DocumentProfile


class VisionClassifier:
    def __init__(self, provider: ClassificationProvider):
        self.provider = provider

    async def classify(self, content: str | bytes, categories: list[dict[str, str]]) -> DocumentProfile:
        result: ClassificationResult = await self.provider.classify(content, categories)
        return DocumentProfile(
            doc_type=result["doc_type"],
            confidence=result["confidence"],
            metadata={
                "classifier_stage": "vision",
                "reasoning": result.get("reasoning", ""),
                "model": result.get("model", ""),
            },
        )
