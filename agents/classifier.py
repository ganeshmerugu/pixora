from __future__ import annotations
from pixora.agents.state import AgentState
from pixora.classifiers.hybrid import HybridClassifier
from pixora.classifiers.vision import VisionClassifier
from pixora.providers.registry import ProviderRegistry

DOCUMENT_CATEGORIES = [
    {"type": "invoice", "description": "Documents with invoice numbers, line items, and totals"},
    {"type": "receipt", "description": "Transaction receipts with payment details"},
    {"type": "contract", "description": "Legal agreements with terms and signatures"},
    {"type": "form", "description": "Fillable forms with checkboxes and fields"},
    {"type": "scientific_paper", "description": "Academic papers with abstract and references"},
    {"type": "spreadsheet", "description": "Tabular data documents"},
    {"type": "letter", "description": "Correspondence and letters"},
    {"type": "report", "description": "Business or technical reports"},
    {"type": "document", "description": "General document"},
]


class ClassifierAgent:
    def __init__(self, registry: ProviderRegistry | None = None):
        vision_clf = None
        if registry:
            try:
                provider = registry.get("classification")
                vision_clf = VisionClassifier(provider)
            except KeyError:
                pass
        self.classifier = HybridClassifier(vision_classifier=vision_clf)

    async def run(self, state: AgentState) -> AgentState:
        raw_bytes = state.get("raw_bytes", b"")
        filename = state.get("source_filename", "unknown.pdf")

        first_page_text = ""
        doc_tree = state.get("document_tree")
        if doc_tree and doc_tree.get("pages"):
            first_page = doc_tree["pages"][0]
            texts = [r.get("content", "") for r in first_page.get("regions", [])]
            first_page_text = "\n".join(texts)

        # Try Jev classification first (calibrated probabilities, no hallucination)
        from pixora.providers.typesafe_jev import is_available as jev_available, classify_document
        if jev_available() and first_page_text.strip():
            try:
                jev_result = await classify_document(first_page_text)
                if jev_result.get("confidence", 0) > 0.5:
                    profile = {
                        "doc_type": jev_result["doc_type"],
                        "confidence": jev_result["confidence"],
                        "reasoning": f"Jev classification with {jev_result['confidence']:.0%} confidence",
                        "has_table": jev_result.get("has_table", 0) > 0.5,
                        "has_handwriting": jev_result.get("has_handwriting", 0) > 0.5,
                        "probabilities": jev_result.get("probabilities", {}),
                    }
                    state["profile"] = profile
                    state.setdefault("decision_trace", []).append({
                        "agent": "classifier",
                        "provider": "jev",
                        "doc_type": profile["doc_type"],
                        "confidence": profile["confidence"],
                    })
                    return state
            except Exception:
                pass

        profile = await self.classifier.classify(
            filename=filename,
            first_page_text=first_page_text,
            raw_bytes=raw_bytes if raw_bytes else None,
            categories=DOCUMENT_CATEGORIES,
        )

        state["profile"] = profile
        state.setdefault("decision_trace", []).append({
            "agent": "classifier",
            "doc_type": profile["doc_type"],
            "confidence": profile["confidence"],
        })

        return state
