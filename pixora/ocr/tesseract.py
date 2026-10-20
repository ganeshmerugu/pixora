from __future__ import annotations
import asyncio
import io
import logging
import uuid
from PIL import Image
import pytesseract
from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 30


class TesseractEngine(OCREngine):
    engine_name = "tesseract"

    def __init__(self, tesseract_cmd: str | None = None, timeout: float = DEFAULT_TIMEOUT_S):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.timeout = timeout

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        if not image_bytes:
            logger.warning("tesseract: empty image_bytes received")
            return []

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._recognize_sync, image_bytes, languages, page_number),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error("tesseract: recognition timed out after %.1fs", self.timeout)
            return []
        except Exception as exc:
            logger.error("tesseract: recognition failed: %s", exc)
            return []

    def _recognize_sync(
        self,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
    ) -> list[RecognizedRegion]:
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:
            logger.error("tesseract: failed to open image: %s", exc)
            return []

        # OSD: detect orientation and script before OCR
        image = self._fix_orientation(image)

        lang = "+".join(languages) if languages else "eng"

        # Use --psm 3 (auto page segmentation) for better multi-column handling
        custom_config = r"--psm 3 --oem 1"
        data = pytesseract.image_to_data(
            image, lang=lang, output_type=pytesseract.Output.DICT,
            config=custom_config,
        )

        words: list[RecognizedWord] = []
        full_text_parts: list[str] = []
        confidences: list[float] = []

        # Group by block_num for reading order (multi-column aware)
        blocks: dict[int, list[tuple[int, str, float, dict]]] = {}
        n = len(data.get("text", []))
        for i in range(n):
            text = str(data["text"][i]).strip()
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                continue
            if not text or conf < 0:
                continue

            block_num = data.get("block_num", [0] * n)[i]
            if block_num not in blocks:
                blocks[block_num] = []
            blocks[block_num].append((i, text, conf, {
                "left": data["left"][i], "top": data["top"][i],
                "width": data["width"][i], "height": data["height"][i],
            }))

        # Sort blocks by vertical position then horizontal (reading order)
        sorted_blocks = sorted(blocks.items(), key=lambda b: (
            min(item[3]["top"] for item in b[1]),
            min(item[3]["left"] for item in b[1]),
        ))

        for _block_num, items in sorted_blocks:
            for _idx, text, conf, bbox_data in items:
                norm_conf = conf / 100.0
                words.append(RecognizedWord(
                    text=text,
                    confidence=norm_conf,
                    bbox=BoundingBox(
                        x=float(bbox_data["left"]),
                        y=float(bbox_data["top"]),
                        width=float(bbox_data["width"]),
                        height=float(bbox_data["height"]),
                        page=page_number,
                    ),
                ))
                full_text_parts.append(text)
                confidences.append(norm_conf)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return [RecognizedRegion(
            region_id=f"tess_{page_number}_{uuid.uuid4().hex[:8]}",
            text=" ".join(full_text_parts),
            confidence=avg_confidence,
            words=words,
            engine="tesseract",
        )]

    @staticmethod
    def _fix_orientation(image: Image.Image) -> Image.Image:
        try:
            osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            rotation = osd.get("rotate", 0)
            if rotation and rotation != 0:
                image = image.rotate(-rotation, expand=True)
                logger.debug("tesseract: OSD rotated image by %d degrees", rotation)
        except Exception:
            pass
        return image
