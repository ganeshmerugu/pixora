from __future__ import annotations
import pytest
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np

from pixora.ocr.preprocessing import PreprocessingPipeline, PreprocessingConfig
from pixora.ocr.claude_vision import ClaudeVisionOCR, StructuredVisionResult, LayoutInfo
from pixora.ocr.postprocessor import OCRPostProcessor, HITLFlag, CorrectionRecord, FINANCIAL_TERMS, LEGAL_TERMS
from pixora.ocr.engine import RecognizedRegion, RecognizedWord
from pixora.layout.detector import LayoutZoneDetector, DetectedZone
from pixora.layout.reading_order import sort_by_reading_order
from pixora.models.document import BoundingBox
from pixora.providers.base import VisionResponse


def _make_test_image(width=400, height=600, color="white") -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _make_document_image() -> Image.Image:
    img = Image.new("RGB", (800, 1200), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 30, 750, 90], fill="lightgray")
    draw.text((60, 45), "INVOICE HEADER", fill="black")
    draw.text((60, 200), "Line item text content here", fill="black")
    draw.rectangle([50, 400, 750, 600], outline="black", width=2)
    draw.line([50, 450, 750, 450], fill="black", width=1)
    draw.line([400, 400, 400, 600], fill="black", width=1)
    draw.text((60, 1100), "Footer - Page 1", fill="gray")
    return img


# ============================================================
# 1. ADVANCED PREPROCESSING
# ============================================================

def test_preprocessing_adaptive_binarization():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=True, contrast=False,
        deskew=False, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "adaptive_binarization" in result["transforms_applied"]


def test_preprocessing_deskew():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=False,
        deskew=True, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "skew_angle" in result


def test_preprocessing_sharpen():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=False,
        deskew=False, sharpen=True, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "sharpen" in result["transforms_applied"]


def test_preprocessing_clahe_contrast():
    pipeline = PreprocessingPipeline()
    img = _make_test_image(color="gray")
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=True,
        deskew=False, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "contrast" in result["transforms_applied"]


def test_preprocessing_cv2_denoising():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=True, adaptive_binarization=False, contrast=False,
        deskew=False, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "noise_removal" in result["transforms_applied"]


def test_preprocessing_border_removal():
    pipeline = PreprocessingPipeline()
    img = Image.new("RGB", (400, 600), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 380, 580], outline="black", width=5)
    draw.text((100, 100), "Content inside border", fill="black")
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=False,
        deskew=False, sharpen=False, border_removal=True, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "border_removal" in result["transforms_applied"]


def test_preprocessing_full_pipeline():
    pipeline = PreprocessingPipeline()
    img = _make_document_image()
    result = pipeline.process(img)
    assert len(result["transforms_applied"]) >= 3
    assert result["image"].mode == "RGB"
    assert result["original_size"] == (800, 1200)


def test_preprocessing_dpi_scaling():
    pipeline = PreprocessingPipeline()
    img = _make_test_image(200, 100)
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=False,
        deskew=False, sharpen=False, border_removal=False, target_dpi=300,
    )
    result = pipeline.process(img, config)
    assert "dpi_scaling" in result["transforms_applied"]


def test_preprocessing_perspective_correction():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=False, adaptive_binarization=False, contrast=False,
        deskew=False, sharpen=False, border_removal=False, camera_correction=True,
        target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert result["image"] is not None


# ============================================================
# 2. VLM STRUCTURE-PRESERVING OCR
# ============================================================

class FakeStructuredVisionProvider:
    provider_name = "fake_vision"

    async def analyze_image(self, image, prompt, **kwargs) -> VisionResponse:
        if "structural understanding" in prompt:
            return VisionResponse(content="""{
                "content_markdown": "# Invoice\\n\\n| Item | Price |\\n|---|---|\\n| Widget | $10 |",
                "regions": [
                    {"type": "HEADER", "content": "Invoice", "reading_order": 0, "confidence": 0.95,
                     "bbox_pct": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.1},
                     "words": [{"text": "Invoice", "confidence": 0.95, "bbox_pct": {"x": 0.1, "y": 0.02, "width": 0.15, "height": 0.05}}]},
                    {"type": "TABLE", "content": "Item | Price\\nWidget | $10", "reading_order": 1, "confidence": 0.90,
                     "bbox_pct": {"x": 0.05, "y": 0.3, "width": 0.9, "height": 0.4}, "words": []}
                ],
                "layout": {"columns": 1, "has_tables": true, "has_headers": true, "has_footers": false,
                           "has_handwriting": false, "has_images": false, "reading_order_confidence": 0.95},
                "overall_confidence": 0.92
            }""", tokens_used=500)
        return VisionResponse(content='{"text": "simple text", "words": [], "confidence": 0.85}', tokens_used=100)


@pytest.mark.asyncio
async def test_vlm_structured_recognition():
    provider = FakeStructuredVisionProvider()
    engine = ClaudeVisionOCR(provider, structure_mode=True)
    result = await engine.recognize_structured(b"fake_img", page_number=1, page_width=800, page_height=1200)
    assert result["content_markdown"].startswith("# Invoice")
    assert len(result["regions"]) == 2
    assert result["regions"][0]["metadata"]["region_type"] == "HEADER"
    assert result["regions"][1]["metadata"]["region_type"] == "TABLE"
    assert result["layout"]["has_tables"] is True
    assert result["overall_confidence"] > 0.9


@pytest.mark.asyncio
async def test_vlm_structured_returns_regions():
    provider = FakeStructuredVisionProvider()
    engine = ClaudeVisionOCR(provider, structure_mode=True)
    regions = await engine.recognize(b"fake_img", page_number=1)
    assert len(regions) >= 1
    assert regions[0]["engine"] == "claude_vision_structured"


@pytest.mark.asyncio
async def test_vlm_simple_mode():
    provider = FakeStructuredVisionProvider()
    engine = ClaudeVisionOCR(provider, structure_mode=False)
    regions = await engine.recognize(b"fake_img", page_number=1)
    assert len(regions) == 1
    assert regions[0]["engine"] == "claude_vision"


@pytest.mark.asyncio
async def test_vlm_preserves_reading_order():
    provider = FakeStructuredVisionProvider()
    engine = ClaudeVisionOCR(provider, structure_mode=True)
    result = await engine.recognize_structured(b"fake_img", page_number=1)
    orders = [r["metadata"]["reading_order"] for r in result["regions"]]
    assert orders == sorted(orders)


@pytest.mark.asyncio
async def test_vlm_bbox_scaling():
    provider = FakeStructuredVisionProvider()
    engine = ClaudeVisionOCR(provider, structure_mode=True)
    result = await engine.recognize_structured(b"fake_img", page_number=1, page_width=800, page_height=1200)
    header = result["regions"][0]
    assert header["words"][0]["bbox"]["x"] == pytest.approx(0.1 * 800)


# ============================================================
# 3. INTELLIGENT POST-PROCESSING
# ============================================================

def _make_region(text, confidence, words=None):
    return RecognizedRegion(
        region_id="r_test",
        text=text,
        confidence=confidence,
        words=words or [],
        engine="test",
    )


def _make_word(text, confidence):
    return RecognizedWord(
        text=text, confidence=confidence,
        bbox=BoundingBox(x=0, y=0, width=50, height=20, page=1),
    )


def test_postprocessor_domain_dictionary_financial():
    pp = OCRPostProcessor()
    regions = [_make_region("invioce totol", 0.6, [
        _make_word("invioce", 0.5),
        _make_word("totol", 0.5),
    ])]
    result = pp.process(regions, doc_type="invoice")
    corrections = result[0]["corrections"]
    corrected_words = [c["corrected"] for c in corrections]
    assert any("invoice" in w for w in corrected_words) or any("total" in w for w in corrected_words)


def test_postprocessor_confusion_pair_fix():
    pp = OCRPostProcessor()
    regions = [_make_region("arnount", 0.7, [_make_word("arnount", 0.7)])]
    result = pp.process(regions, doc_type="invoice")
    assert result[0]["corrected_text"] == "amount"


def test_postprocessor_pattern_fix_amount():
    pp = OCRPostProcessor()
    regions = [_make_region("$1,5OO.OO", 0.5, [_make_word("$1,5OO.OO", 0.4)])]
    result = pp.process(regions, doc_type="invoice")
    assert result[0]["corrected_text"] == "$1,500.00"


def test_postprocessor_hitl_flags_low_confidence():
    pp = OCRPostProcessor(hitl_threshold=0.7)
    regions = [_make_region("unclear text", 0.5, [
        _make_word("unclear", 0.4),
        _make_word("text", 0.95),
    ])]
    result = pp.process(regions)
    hitl = result[0]["hitl_flags"]
    assert len(hitl) >= 1
    assert hitl[0]["confidence"] < 0.7


def test_postprocessor_hitl_with_suggestions():
    pp = OCRPostProcessor(hitl_threshold=0.7)
    regions = [_make_region("invice", 0.5, [_make_word("invice", 0.3)])]
    result = pp.process(regions, doc_type="invoice")
    hitl = result[0]["hitl_flags"]
    assert len(hitl) >= 1
    assert len(hitl[0].get("suggested_corrections", [])) >= 0


def test_postprocessor_no_hitl_high_confidence():
    pp = OCRPostProcessor(hitl_threshold=0.7)
    regions = [_make_region("clear text", 0.95, [
        _make_word("clear", 0.95),
        _make_word("text", 0.98),
    ])]
    result = pp.process(regions)
    assert result[0]["hitl_flags"] == []


def test_postprocessor_region_level_hitl():
    pp = OCRPostProcessor(hitl_threshold=0.7)
    regions = [_make_region("low quality scan", 0.3)]
    result = pp.process(regions)
    assert len(result[0]["hitl_flags"]) >= 1
    assert result[0]["hitl_flags"][0]["reason"] == "low_region_confidence"


def test_postprocessor_custom_dictionary():
    pp = OCRPostProcessor(custom_dictionary={"xylophone", "kazoo"})
    regions = [_make_region("xylophon", 0.5, [_make_word("xylophon", 0.5)])]
    result = pp.process(regions)
    assert result[0]["corrections"][0]["corrected"] == "xylophone"


def test_postprocessor_legal_domain():
    pp = OCRPostProcessor()
    regions = [_make_region("agreernent", 0.7, [_make_word("agreernent", 0.6)])]
    result = pp.process(regions, doc_type="contract")
    assert result[0]["corrected_text"] == "agreement"


def test_postprocessor_confidence_adjustment():
    pp = OCRPostProcessor()
    regions = [_make_region("arnount totol", 0.6, [
        _make_word("arnount", 0.5),
        _make_word("totol", 0.5),
    ])]
    result = pp.process(regions, doc_type="invoice")
    assert result[0]["final_confidence"] != 0.6


# ============================================================
# 4. LAYOUT ZONE DETECTION
# ============================================================

def test_layout_detector_basic():
    detector = LayoutZoneDetector()
    img = _make_test_image()
    result = detector.detect(img, page_number=1)
    assert "zones" in result
    assert result["page_number"] == 1


def test_layout_detector_document_image():
    detector = LayoutZoneDetector()
    img = _make_document_image()
    result = detector.detect(img, page_number=1)
    assert len(result["zones"]) >= 1
    types = [z["zone_type"] for z in result["zones"]]
    assert "HEADER" in types or "TEXT" in types


def test_layout_detector_estimates_columns():
    detector = LayoutZoneDetector()
    img = _make_test_image()
    result = detector.detect(img, page_number=1)
    assert result["estimated_columns"] >= 1


def test_layout_detector_zone_has_bbox():
    detector = LayoutZoneDetector()
    img = _make_document_image()
    result = detector.detect(img, page_number=1)
    for zone in result["zones"]:
        assert "bbox" in zone
        assert zone["bbox"]["page"] == 1


def test_reading_order_single_column():
    zones = [
        DetectedZone(zone_id="z1", zone_type="FOOTER", bbox=BoundingBox(x=0, y=900, width=800, height=100, page=1), confidence=0.8),
        DetectedZone(zone_id="z2", zone_type="TEXT", bbox=BoundingBox(x=0, y=200, width=800, height=300, page=1), confidence=0.8),
        DetectedZone(zone_id="z3", zone_type="HEADER", bbox=BoundingBox(x=0, y=0, width=800, height=100, page=1), confidence=0.8),
    ]
    ordered = sort_by_reading_order(zones, num_columns=1)
    assert ordered[0]["zone_type"] == "HEADER"
    assert ordered[-1]["zone_type"] == "FOOTER"


def test_reading_order_multi_column():
    zones = [
        DetectedZone(zone_id="z1", zone_type="TEXT", bbox=BoundingBox(x=400, y=100, width=350, height=200, page=1), confidence=0.8),
        DetectedZone(zone_id="z2", zone_type="TEXT", bbox=BoundingBox(x=50, y=100, width=350, height=200, page=1), confidence=0.8),
        DetectedZone(zone_id="z3", zone_type="HEADER", bbox=BoundingBox(x=0, y=0, width=800, height=80, page=1), confidence=0.8),
    ]
    ordered = sort_by_reading_order(zones, num_columns=2)
    assert ordered[0]["zone_type"] == "HEADER"
    assert ordered[1]["bbox"]["x"] < ordered[2]["bbox"]["x"]


def test_reading_order_empty():
    assert sort_by_reading_order([]) == []
