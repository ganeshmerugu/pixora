"""Smart document routing — informed by ParseBench benchmarks.

Key insight from ParseBench:
  - Digital PDFs with text layers: direct extraction = 94.4%, OCR = 0%
  - Scanned documents: OCR required, ensemble > single engine
  - Tables: need structural parser (docling/doctr), not plain OCR
  - Charts: need VLM, OCR is useless
  - Handwriting: need VLM (Claude Vision / Qwen-VL)

Routing priority: cheapest strategy that meets quality bar.
"""
from __future__ import annotations
from pixora.agents.state import AgentState
from pixora.models.pipeline import ProcessingPlan, DocumentProfile
from pixora.config.settings import settings


OCR_STRATEGY_TEXT_DIRECT = "TEXT_DIRECT"
OCR_STRATEGY_TESSERACT = "TESSERACT_ONLY"
OCR_STRATEGY_ENSEMBLE = "ENSEMBLE"
OCR_STRATEGY_SURYA = "SURYA_PRIMARY"
OCR_STRATEGY_DOCTR = "DOCTR_PRIMARY"
OCR_STRATEGY_GOT_OCR = "GOT_OCR_PRIMARY"
OCR_STRATEGY_VLM = "VLM_PRIMARY"
OCR_STRATEGY_CLAUDE_VISION = "CLAUDE_VISION_PRIMARY"


def build_processing_plan(profile: DocumentProfile) -> ProcessingPlan:
    is_scanned = profile.get("is_scanned", False)
    has_text_layer = profile.get("text_layer_present", not is_scanned)
    has_handwriting = profile.get("has_handwriting", False)
    has_tables = profile.get("has_tables", False)
    has_images = profile.get("has_images", False)
    complexity = profile.get("complexity", 0.5)
    if isinstance(complexity, str):
        try:
            complexity = float(complexity)
        except ValueError:
            complexity = 0.5
    gpu = settings.gpu_enabled
    page_count = profile.get("page_count", 1)

    # ── Rule 1: Handwritten documents → VLM required ────────────
    if has_handwriting:
        if gpu:
            return _plan(OCR_STRATEGY_VLM, "deep", 4, 0.85, "handwriting_gpu", 2)
        return _plan(OCR_STRATEGY_CLAUDE_VISION, "deep", 4, 0.85, "handwriting_api", 3)

    # ── Rule 2: Digital PDF with text layer → skip OCR entirely ──
    # ParseBench proved: direct text = 94.4% vs Tesseract OCR = 0%
    if has_text_layer and not is_scanned:
        if has_tables and complexity >= 0.4:
            return _plan(OCR_STRATEGY_TEXT_DIRECT, "standard", 2, 0.82,
                         "digital_text_layer_tables", 1)
        if complexity < 0.3:
            return _plan(OCR_STRATEGY_TEXT_DIRECT, "fast", 1, 0.80,
                         "digital_text_layer_simple", 1)
        return _plan(OCR_STRATEGY_TEXT_DIRECT, "standard", 2, 0.80,
                     "digital_text_layer", 1)

    # ── Rule 3: Scanned with tables → structural parser ──────────
    if is_scanned and has_tables:
        if gpu:
            return _plan(OCR_STRATEGY_DOCTR, "deep", 3, 0.82,
                         "scanned_tables_gpu", 2)
        return _plan(OCR_STRATEGY_ENSEMBLE, "standard", 3, 0.78,
                     "scanned_tables_cpu", 1)

    # ── Rule 4: Complex scanned documents → best available OCR ───
    if is_scanned and complexity >= 0.5:
        if gpu:
            return _plan(OCR_STRATEGY_SURYA, "deep", 3, 0.85,
                         "complex_scanned_gpu", 2)
        return _plan(OCR_STRATEGY_ENSEMBLE, "standard", 3, 0.80,
                     "complex_scanned_cpu", 1)

    # ── Rule 5: Simple scanned documents → Tesseract is enough ───
    if is_scanned and complexity < 0.3:
        return _plan(OCR_STRATEGY_TESSERACT, "fast", 2, 0.75,
                     "simple_scanned", 1)

    # ── Rule 6: Standard scanned → ensemble for reliability ──────
    if is_scanned:
        return _plan(OCR_STRATEGY_ENSEMBLE, "standard", 3, 0.80,
                     "scanned_standard", 1)

    # ── Rule 7: Image files (PNG/JPG) → always need OCR ─────────
    if has_images and not has_text_layer:
        if gpu:
            return _plan(OCR_STRATEGY_SURYA, "standard", 2, 0.80,
                         "image_file_gpu", 2)
        return _plan(OCR_STRATEGY_TESSERACT, "standard", 2, 0.75,
                     "image_file_cpu", 1)

    # ── Rule 8: Multi-page digital → direct text, more rounds ────
    if page_count > 10:
        return _plan(OCR_STRATEGY_TEXT_DIRECT, "deep", 3, 0.82,
                     "multipage_digital", 1)

    # ── Default: direct text extraction (digital document) ───────
    return _plan(OCR_STRATEGY_TEXT_DIRECT, "standard", 2, 0.80,
                 "default_digital", 1)


def _plan(
    strategy: str,
    mode: str,
    rounds: int,
    quality: float,
    reason: str,
    tier: int,
) -> ProcessingPlan:
    return ProcessingPlan(
        ocr_strategy=strategy,
        extraction_mode=mode,
        max_correction_rounds=rounds,
        target_quality=quality,
        metadata={"reason": reason, "tier_hint": tier},
    )


class RouterAgent:
    async def run(self, state: AgentState) -> AgentState:
        profile = state.get("profile")
        if not profile:
            profile = DocumentProfile(doc_type="document", confidence=0.3)
            state["profile"] = profile

        doc_tree = state.get("document_tree", {})
        if doc_tree and "text_layer_present" not in profile:
            has_text = any(
                region.get("content", "").strip()
                for page in doc_tree.get("pages", [])
                for region in page.get("regions", [])
            )
            profile["text_layer_present"] = has_text

        plan = build_processing_plan(profile)
        state["processing_plan"] = plan
        state["max_correction_rounds"] = plan.get("max_correction_rounds", 3)

        state.setdefault("decision_trace", []).append({
            "agent": "router",
            "ocr_strategy": plan["ocr_strategy"],
            "extraction_mode": plan["extraction_mode"],
            "tier_hint": plan.get("metadata", {}).get("tier_hint", 1),
            "reason": plan.get("metadata", {}).get("reason", ""),
            "text_layer_detected": profile.get("text_layer_present", False),
        })

        return state
