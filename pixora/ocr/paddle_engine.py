"""PaddleOCR engine — PP-OCRv5 for multi-language text + PP-StructureV3 for layout/markdown."""
from __future__ import annotations
import io
import uuid
import threading
from typing import Any
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.models.document import BoundingBox

_ocr_cache: dict[str, Any] = {}
_structure_cache: dict[str, Any] = {}
_lock = threading.Lock()


def _get_ocr(lang: str = "en") -> Any:
    from paddleocr import PaddleOCR
    if lang not in _ocr_cache:
        with _lock:
            if lang not in _ocr_cache:
                _ocr_cache[lang] = PaddleOCR(
                    lang=lang,
                    use_doc_orientation_classify=True,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                )
    return _ocr_cache[lang]


def _get_structure() -> Any:
    if "default" not in _structure_cache:
        with _lock:
            if "default" not in _structure_cache:
                try:
                    from paddleocr import PPStructureV3
                    _structure_cache["default"] = PPStructureV3(
                        use_table_recognition=True,
                        use_seal_recognition=True,
                        use_formula_recognition=False,
                    )
                except ImportError:
                    _structure_cache["default"] = None
    return _structure_cache["default"]


LANG_MAP = {
    "en": "en", "hi": "hi", "mr": "mr", "ne": "ne",
    "ar": "ar", "fa": "fa", "ur": "ur",
    "zh": "ch", "ja": "japan", "ko": "korean",
    "ta": "ta", "te": "te", "kn": "kn",
    "ru": "ru", "de": "german", "fr": "fr", "es": "es",
    "pt": "pt", "it": "it", "nl": "nl",
    "th": "th", "vi": "vi", "ms": "ms",
    "bn": "bn", "gu": "gu", "pa": "pa",
}


class PaddleOCREngine(OCREngine):
    engine_name = "paddleocr"

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        langs = languages or ["en"]
        paddle_lang = LANG_MAP.get(langs[0], "en")

        ocr = _get_ocr(paddle_lang)

        from PIL import Image
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)

        results = ocr.predict(img_array)

        all_words: list[RecognizedWord] = []
        all_text_parts: list[str] = []
        all_confidences: list[float] = []

        for res in results:
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
            rec_boxes = res.get("rec_boxes", [])

            for i, text in enumerate(rec_texts):
                if not text.strip():
                    continue
                conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                if conf < 0.3:
                    continue

                box = rec_boxes[i] if i < len(rec_boxes) else None
                bbox = BoundingBox(x=0, y=0, width=0, height=0, page=page_number)
                if box is not None:
                    try:
                        coords = list(box)
                        if len(coords) >= 4:
                            x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                            bbox = BoundingBox(
                                x=x1, y=y1,
                                width=x2 - x1, height=y2 - y1,
                                page=page_number,
                            )
                    except (TypeError, ValueError):
                        pass

                all_words.append(RecognizedWord(
                    text=text, confidence=conf, bbox=bbox,
                ))
                all_text_parts.append(text)
                all_confidences.append(conf)

        avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return [RecognizedRegion(
            region_id=f"paddle_{page_number}_{uuid.uuid4().hex[:8]}",
            text=" ".join(all_text_parts),
            confidence=avg_conf,
            words=all_words,
            engine="paddleocr",
        )]


async def paddle_to_markdown(file_path_or_bytes: bytes | str) -> dict[str, Any]:
    pipeline = _get_structure()
    if pipeline is None:
        return {"markdown": "", "items": [], "error": "PPStructureV3 not available"}

    import tempfile
    import os

    if isinstance(file_path_or_bytes, bytes):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(file_path_or_bytes)
        tmp.close()
        input_path = tmp.name
        cleanup = True
    else:
        input_path = file_path_or_bytes
        cleanup = False

    try:
        results = pipeline.predict(input=input_path)

        pages_md = []
        all_items = []

        for page_idx, res in enumerate(results):
            md = getattr(res, "markdown", "") or ""
            pages_md.append(md)

            layout_regions = []
            if hasattr(res, "layout_result") and res.layout_result:
                layout_regions = res.layout_result
            elif isinstance(res, dict):
                layout_regions = res.get("layout_result", [])

            for region in layout_regions:
                if isinstance(region, dict):
                    item = {
                        "type": _map_label_to_type(region.get("label", "text")),
                        "label": region.get("label", "text"),
                        "value": region.get("text", ""),
                        "md": region.get("md", region.get("text", "")),
                        "level": 2 if "title" in region.get("label", "") else None,
                        "bbox": {
                            "x": region.get("coordinate", [0])[0] if region.get("coordinate") else 0,
                            "y": region.get("coordinate", [0, 0])[1] if region.get("coordinate") and len(region.get("coordinate", [])) > 1 else 0,
                            "w": (region.get("coordinate", [0, 0, 0])[2] - region.get("coordinate", [0])[0]) if region.get("coordinate") and len(region.get("coordinate", [])) > 2 else 0,
                            "h": (region.get("coordinate", [0, 0, 0, 0])[3] - region.get("coordinate", [0, 0])[1]) if region.get("coordinate") and len(region.get("coordinate", [])) > 3 else 0,
                            "confidence": region.get("score", 0.0),
                            "label": region.get("label", "text"),
                        },
                        "page": page_idx + 1,
                    }
                    all_items.append(item)

        try:
            full_md = pipeline.concatenate_markdown_pages(pages_md)
        except Exception:
            full_md = "\n\n---\n\n".join(pages_md)

        return {"markdown": full_md, "items": all_items, "pages_md": pages_md}
    except Exception as e:
        return {"markdown": "", "items": [], "error": str(e)}
    finally:
        if cleanup:
            try:
                os.unlink(input_path)
            except Exception:
                pass


def _map_label_to_type(label: str) -> str:
    label_lower = label.lower()
    if "title" in label_lower or "header" in label_lower:
        return "heading"
    if "table" in label_lower:
        return "table"
    if "image" in label_lower or "figure" in label_lower:
        return "image"
    if "seal" in label_lower:
        return "image"
    if "formula" in label_lower:
        return "text"
    return "text"
