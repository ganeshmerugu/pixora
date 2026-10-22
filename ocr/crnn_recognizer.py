"""CRNN + CTC text recognizer.

Architecture:
  Cropped ROI (32 x W) -> CNN (7 conv layers) -> Feature Map (512 x 1 x T)
  -> Map-to-Sequence (T x 512)
  -> Bi-LSTM (2-layer, hidden=256) -> (T x 512)
  -> Linear + Softmax -> (T x |alphabet + blank|)
  -> CTC decoding -> text string

Requires PyTorch. Falls back to Tesseract when unavailable.
"""
from __future__ import annotations
import asyncio
import io
import logging
import uuid
from typing import Any

import numpy as np
from PIL import Image

from pixora.ocr.engine import OCREngine, RecognizedRegion, RecognizedWord
from pixora.ocr.ctc_decoder import (
    greedy_decode,
    BeamSearchDecoder,
    NGramLM,
    DEFAULT_ALPHABET,
)
from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

IMG_HEIGHT = 32
ALPHABET = DEFAULT_ALPHABET
NUM_CLASSES = len(ALPHABET) + 1


if HAS_TORCH:

    class _CNNBackbone(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(3, 64, 3, stride=1, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),

                nn.Conv2d(64, 128, 3, stride=1, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),

                nn.Conv2d(128, 256, 3, stride=1, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),

                nn.Conv2d(256, 256, 3, stride=1, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                nn.MaxPool2d((2, 1), (2, 1)),

                nn.Conv2d(256, 512, 3, stride=1, padding=1),
                nn.BatchNorm2d(512),
                nn.ReLU(inplace=True),

                nn.Conv2d(512, 512, 3, stride=1, padding=1),
                nn.BatchNorm2d(512),
                nn.ReLU(inplace=True),
                nn.MaxPool2d((2, 1), (2, 1)),

                nn.Conv2d(512, 512, 2, stride=1, padding=0),
                nn.BatchNorm2d(512),
                nn.ReLU(inplace=True),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.layers(x)


    class CRNN(nn.Module):
        def __init__(self, num_classes: int = NUM_CLASSES, hidden_size: int = 256):
            super().__init__()
            self.cnn = _CNNBackbone()
            self.rnn = nn.LSTM(
                input_size=512,
                hidden_size=hidden_size,
                num_layers=2,
                bidirectional=True,
                batch_first=True,
            )
            self.fc = nn.Linear(hidden_size * 2, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            conv = self.cnn(x)
            b, c, h, t = conv.shape
            seq = conv.squeeze(2).permute(0, 2, 1)
            rnn_out, _ = self.rnn(seq)
            logits = self.fc(rnn_out)
            return torch.log_softmax(logits, dim=2)


class CRNNRecognizer(OCREngine):
    engine_name = "crnn"

    def __init__(
        self,
        weights_path: str | None = None,
        device: str = "cpu",
        use_beam_search: bool = True,
        beam_width: int = 10,
        lm: NGramLM | None = None,
        lm_weight: float = 0.3,
    ):
        self._available = HAS_TORCH
        self.device = device
        self.use_beam_search = use_beam_search

        if HAS_TORCH:
            self.model = CRNN(num_classes=NUM_CLASSES)
            if weights_path:
                state = torch.load(weights_path, map_location=device, weights_only=True)
                self.model.load_state_dict(state)
                logger.info("crnn: loaded weights from %s", weights_path)
            self.model.to(device)
            self.model.eval()
        else:
            self.model = None

        self.decoder = BeamSearchDecoder(
            alphabet=ALPHABET,
            beam_width=beam_width,
            lm=lm,
            lm_weight=lm_weight,
        ) if use_beam_search else None

    async def recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
        page_number: int = 1,
    ) -> list[RecognizedRegion]:
        if not self._available or self.model is None:
            return await self._fallback_recognize(image_bytes, languages, page_number)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._recognize_sync, image_bytes, page_number,
        )

    def _recognize_sync(
        self, image_bytes: bytes, page_number: int,
    ) -> list[RecognizedRegion]:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            logger.error("crnn: failed to open image: %s", exc)
            return []

        w_orig, h_orig = image.size
        scale = IMG_HEIGHT / h_orig
        new_w = max(int(w_orig * scale), 1)
        resized = image.resize((new_w, IMG_HEIGHT))

        arr = np.array(resized).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            log_probs = self.model(tensor)

        log_probs_np = log_probs.squeeze(0).cpu().numpy()

        if self.decoder:
            text = self.decoder.decode(log_probs_np)
        else:
            text = greedy_decode(log_probs_np, ALPHABET)

        frame_max = np.max(log_probs_np, axis=1)
        confidence = float(np.mean(np.exp(frame_max)))

        return [RecognizedRegion(
            region_id=f"crnn_{page_number}_{uuid.uuid4().hex[:8]}",
            text=text,
            confidence=round(confidence, 4),
            words=[],
            engine="crnn",
            metadata={"frames": int(log_probs_np.shape[0])},
        )]

    async def _fallback_recognize(
        self,
        image_bytes: bytes,
        languages: list[str] | None,
        page_number: int,
    ) -> list[RecognizedRegion]:
        try:
            from pixora.ocr.tesseract import TesseractEngine
            engine = TesseractEngine()
            return await engine.recognize(image_bytes, languages, page_number)
        except Exception as exc:
            logger.warning("crnn: fallback to tesseract failed: %s", exc)
            return []
