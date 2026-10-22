"""Page orientation classifier.

Predicts rotation angle in {0, 90, 180, 270} degrees.
Uses a lightweight CNN when PyTorch is available, otherwise falls back
to Hough-line text angle heuristics.
"""
from __future__ import annotations
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

ANGLES = [0, 90, 180, 270]
INPUT_SIZE = 128


if HAS_TORCH:

    class _OrientationCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 32, 3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(32, 64, 3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 128, 3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(128, 128, 3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d(1),
            )
            self.classifier = nn.Linear(128, 4)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            f = self.features(x).flatten(1)
            return self.classifier(f)


class OrientationClassifier:
    def __init__(self, weights_path: str | None = None, device: str = "cpu"):
        self._model = None
        self.device = device

        if HAS_TORCH:
            self._model = _OrientationCNN()
            if weights_path:
                state = torch.load(weights_path, map_location=device, weights_only=True)
                self._model.load_state_dict(state)
                logger.info("orientation: loaded weights from %s", weights_path)
            self._model.to(device)
            self._model.eval()

    def predict(self, image: Image.Image) -> tuple[int, float]:
        if self._model is not None and HAS_TORCH:
            return self._predict_cnn(image)
        return self._predict_heuristic(image)

    def _predict_cnn(self, image: Image.Image) -> tuple[int, float]:
        gray = image.convert("L").resize((INPUT_SIZE, INPUT_SIZE))
        arr = np.array(gray, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze()

        idx = int(probs.argmax())
        conf = float(probs[idx])
        return ANGLES[idx], conf

    def _predict_heuristic(self, image: Image.Image) -> tuple[int, float]:
        if not HAS_CV2:
            return 0, 0.5

        gray = np.array(image.convert("L"))
        h, w = gray.shape

        scores: list[float] = []
        for test_angle in ANGLES:
            if test_angle == 0:
                rotated = gray
            else:
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, -test_angle, 1.0)
                rotated = cv2.warpAffine(gray, M, (w, h), borderValue=255)

            _, binary = cv2.threshold(rotated, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            proj = np.sum(binary > 0, axis=1).astype(np.float64)

            if len(proj) < 10:
                scores.append(0.0)
                continue

            variance = float(np.var(proj))
            peaks = int(np.sum(np.diff(np.sign(np.diff(proj))) < 0))
            scores.append(variance * (peaks + 1))

        best_idx = int(np.argmax(scores))
        total = sum(scores) or 1.0
        confidence = scores[best_idx] / total

        return ANGLES[best_idx], round(min(confidence, 0.99), 4)

    def correct(self, image: Image.Image) -> tuple[Image.Image, int, float]:
        angle, conf = self.predict(image)
        if angle == 0:
            return image, 0, conf
        rotated = image.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
        return rotated, angle, conf
