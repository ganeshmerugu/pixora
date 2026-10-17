from __future__ import annotations
import pytest
from PIL import Image
import io

from pixora.ocr.preprocessing import PreprocessingPipeline, PreprocessingConfig
from pixora.ocr.segmenter import TextSegmenter, SegmentedRegion, SegmentedLine, SegmentedWord
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.ocr.ensemble import OCREnsemble
from pixora.ocr.postprocessor import OCRPostProcessor, PostProcessedRegion
from pixora.ocr.features import FeatureExtractor, FeatureSet
from pixora.ocr.recognizer import TextRecognizer
from pixora.harness.ocr_arbiter import OCRConfidenceArbiter, OCRDisagreement
from pixora.models.document import BoundingBox


def _make_test_image(width: int = 200, height: int = 100, color: str = "white") -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _image_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# --- Preprocessing ---

def test_preprocessing_default_config():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    result = pipeline.process(img)
    assert result["image"] is not None
    assert "noise_removal" in result["transforms_applied"]
    assert "contrast" in result["transforms_applied"]
    assert result["original_size"] == (200, 100)


def test_preprocessing_custom_config():
    pipeline = PreprocessingPipeline()
    img = _make_test_image()
    config = PreprocessingConfig(
        noise_removal=False, binarization=False, adaptive_binarization=False,
        contrast=False, deskew=False, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert result["transforms_applied"] == [] or result["transforms_applied"] == ["exif_orientation"]


def test_preprocessing_binarization():
    pipeline = PreprocessingPipeline()
    img = _make_test_image(color="gray")
    config = PreprocessingConfig(
        noise_removal=False, binarization=False, adaptive_binarization=True,
        contrast=False, deskew=False, sharpen=False, border_removal=False, target_dpi=0,
    )
    result = pipeline.process(img, config)
    assert "adaptive_binarization" in result["transforms_applied"]


def test_preprocessing_grayscale_input():
    pipeline = PreprocessingPipeline()
    img = Image.new("L", (100, 50), 128)
    result = pipeline.process(img)
    assert result["image"].mode == "RGB"


# --- Segmentation ---

def test_segmenter_basic():
    segmenter = TextSegmenter()
    img = _make_test_image()
    result = segmenter.segment(img, page_number=1)
    assert len(result["regions"]) == 1
    assert result["regions"][0]["type"] == "TEXT"
    assert result["page_dimensions"] == (200, 100)


def test_segmenter_from_tsv_data():
    segmenter = TextSegmenter()
    tsv = [
        {"level": "5", "line_num": "1", "left": "10", "top": "20", "width": "50", "height": "15", "text": "hello"},
        {"level": "5", "line_num": "1", "left": "70", "top": "20", "width": "60", "height": "15", "text": "world"},
        {"level": "5", "line_num": "2", "left": "10", "top": "50", "width": "80", "height": "15", "text": "test"},
    ]
    result = segmenter.segment_with_tesseract_data(tsv, page_number=1)
    assert len(result["regions"]) == 1
    region = result["regions"][0]
    assert len(region["lines"]) == 2
    assert len(region["lines"][0]["words"]) == 2


# --- OCR Arbiter ---

def test_arbiter_all_agree():
    arbiter = OCRConfidenceArbiter()
    r1 = RecognizedRegion(region_id="r1", text="hello", confidence=0.9, engine="tesseract")
    r2 = RecognizedRegion(region_id="r2", text="hello", confidence=0.85, engine="vision")
    result = arbiter.merge({"tesseract": [r1], "vision": [r2]})
    assert len(result) == 1
    assert result[0]["text"] == "hello"


def test_arbiter_confidence_gap():
    arbiter = OCRConfidenceArbiter()
    r1 = RecognizedRegion(region_id="r1", text="hello", confidence=0.95, engine="tesseract")
    r2 = RecognizedRegion(region_id="r2", text="helo", confidence=0.6, engine="vision")
    result = arbiter.merge({"tesseract": [r1], "vision": [r2]})
    assert result[0]["text"] == "hello"
    disagreements = arbiter.get_disagreements()
    assert len(disagreements) == 1
    assert disagreements[0]["selection_reason"] == "confidence_gap"


def test_arbiter_region_type_preference():
    arbiter = OCRConfidenceArbiter({"HANDWRITING": "claude_vision"})
    r1 = RecognizedRegion(region_id="r1", text="scrawl", confidence=0.7, engine="tesseract")
    r2 = RecognizedRegion(region_id="r2", text="scroll", confidence=0.65, engine="claude_vision")
    result = arbiter.merge({"tesseract": [r1], "claude_vision": [r2]}, region_type="HANDWRITING")
    assert result[0]["engine"] == "claude_vision"


def test_arbiter_empty_input():
    arbiter = OCRConfidenceArbiter()
    result = arbiter.merge({})
    assert result == []


# --- Ensemble ---

class FakeEngine(OCREngine):
    engine_name = "fake"

    def __init__(self, text: str, confidence: float):
        self._text = text
        self._confidence = confidence

    async def recognize(self, image_bytes, languages=None, page_number=1):
        return [RecognizedRegion(
            region_id=f"{self.engine_name}_1",
            text=self._text,
            confidence=self._confidence,
            engine=self.engine_name,
        )]


class FailingEngine(OCREngine):
    engine_name = "failing"

    async def recognize(self, image_bytes, languages=None, page_number=1):
        raise RuntimeError("Engine failed")


@pytest.mark.asyncio
async def test_ensemble_single_engine():
    eng = FakeEngine("hello world", 0.9)
    ensemble = OCREnsemble([eng])
    result = await ensemble.recognize(b"fake_image")
    assert len(result) == 1
    assert result[0]["text"] == "hello world"


@pytest.mark.asyncio
async def test_ensemble_multiple_engines():
    e1 = FakeEngine("hello world", 0.9)
    e1.engine_name = "engine_a"
    e2 = FakeEngine("hello world", 0.85)
    e2.engine_name = "engine_b"
    ensemble = OCREnsemble([e1, e2])
    result = await ensemble.recognize(b"fake_image")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_ensemble_handles_engine_failure():
    good = FakeEngine("hello", 0.9)
    good.engine_name = "good"
    bad = FailingEngine()
    ensemble = OCREnsemble([good, bad])
    result = await ensemble.recognize(b"fake_image")
    assert len(result) == 1
    assert result[0]["text"] == "hello"


# --- Post-Processor ---

def test_postprocessor_passthrough():
    pp = OCRPostProcessor()
    regions = [RecognizedRegion(region_id="r1", text="hello world", confidence=0.95, words=[
        RecognizedWord(text="hello", confidence=0.95, bbox=BoundingBox(x=0, y=0, width=50, height=20, page=1)),
        RecognizedWord(text="world", confidence=0.95, bbox=BoundingBox(x=60, y=0, width=50, height=20, page=1)),
    ])]
    result = pp.process(regions)
    assert len(result) == 1
    assert result[0]["corrected_text"] == "hello world"
    assert result[0]["corrections"] == []


def test_postprocessor_no_words():
    pp = OCRPostProcessor()
    regions = [RecognizedRegion(region_id="r1", text="raw text", confidence=0.8)]
    result = pp.process(regions)
    assert result[0]["corrected_text"] == "raw text"


def test_postprocessor_low_confidence_correction():
    pp = OCRPostProcessor()
    regions = [RecognizedRegion(region_id="r1", text="$1O.OO", confidence=0.5, words=[
        RecognizedWord(text="$1O.OO", confidence=0.4, bbox=BoundingBox(x=0, y=0, width=50, height=20, page=1)),
    ])]
    result = pp.process(regions, doc_type="invoice")
    assert len(result) == 1


# --- Feature Extractor ---

def test_feature_extractor_engine_internal():
    fe = FeatureExtractor()
    region = SegmentedRegion(id="r1", type="TEXT", bbox=BoundingBox(x=0, y=0, width=100, height=50, page=1))
    result = fe.extract(region)
    assert result["mode"] == "engine_internal"


def test_feature_extractor_classical():
    fe = FeatureExtractor()
    region = SegmentedRegion(id="r1", type="TEXT", bbox=BoundingBox(x=0, y=0, width=100, height=50, page=1))
    result = fe.extract(region, mode="classical")
    assert result["mode"] == "classical"


def test_feature_extractor_deep():
    fe = FeatureExtractor()
    region = SegmentedRegion(id="r1", type="TABLE", bbox=BoundingBox(x=0, y=0, width=100, height=50, page=1))
    result = fe.extract(region, mode="deep")
    assert result["mode"] == "deep"


# --- Recognizer Dispatcher ---

@pytest.mark.asyncio
async def test_recognizer_single_strategy():
    fake = FakeEngine("recognized text", 0.9)
    fake.engine_name = "tesseract"
    recognizer = TextRecognizer(engines={"tesseract": fake})
    result = await recognizer.recognize(b"img", strategy="TESSERACT_ONLY")
    assert len(result) == 1
    assert result[0]["corrected_text"] == "recognized text"


@pytest.mark.asyncio
async def test_recognizer_vision_strategy():
    fake = FakeEngine("vision text", 0.85)
    fake.engine_name = "claude_vision"
    recognizer = TextRecognizer(engines={"claude_vision": fake})
    result = await recognizer.recognize(b"img", strategy="CLAUDE_VISION_PRIMARY")
    assert len(result) == 1
    assert result[0]["corrected_text"] == "vision text"


@pytest.mark.asyncio
async def test_recognizer_ensemble_strategy():
    e1 = FakeEngine("text", 0.9)
    e1.engine_name = "eng1"
    e2 = FakeEngine("text", 0.85)
    e2.engine_name = "eng2"
    ensemble = OCREnsemble([e1, e2])
    recognizer = TextRecognizer(ensemble=ensemble)
    result = await recognizer.recognize(b"img", strategy="ENSEMBLE")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_recognizer_unknown_strategy():
    recognizer = TextRecognizer()
    with pytest.raises(ValueError, match="Unknown OCR strategy"):
        await recognizer.recognize(b"img", strategy="INVALID")


@pytest.mark.asyncio
async def test_recognizer_missing_engine():
    recognizer = TextRecognizer()
    with pytest.raises(KeyError):
        await recognizer.recognize(b"img", strategy="TESSERACT_ONLY")
