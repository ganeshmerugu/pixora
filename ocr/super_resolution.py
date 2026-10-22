"""Super-resolution for low-DPI document images.

ESPCN (Efficient Sub-Pixel Convolutional Network) for 2x upscaling.
Sub-pixel shuffle: rearranges (C*r*r, H, W) -> (C, H*r, W*r).

Only activates when estimated DPI < 150.
Falls back to Lanczos interpolation without PyTorch.
"""
from __future__ import annotations
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

DPI_THRESHOLD = 150
DEFAULT_SCALE = 2


if HAS_TORCH:

    class ESPCN(nn.Module):
        """Efficient Sub-Pixel CNN for single-image super-resolution."""

        def __init__(self, scale_factor: int = 2, num_channels: int = 1):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(num_channels, 64, 5, padding=2),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 64, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 32, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(32, num_channels * scale_factor * scale_factor, 3, padding=1),
                nn.PixelShuffle(scale_factor),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)


def estimate_dpi(image: Image.Image) -> int:
    dpi = image.info.get("dpi")
    if isinstance(dpi, tuple) and dpi[0] > 0:
        return int(dpi[0])
    if isinstance(dpi, (int, float)) and dpi > 0:
        return int(dpi)
    return 72


class SuperResolver:
    def __init__(
        self,
        weights_path: str | None = None,
        device: str = "cpu",
        scale: int = DEFAULT_SCALE,
    ):
        self.scale = scale
        self.device = device
        self._model = None

        if HAS_TORCH:
            self._model = ESPCN(scale_factor=scale)
            if weights_path:
                state = torch.load(weights_path, map_location=device, weights_only=True)
                self._model.load_state_dict(state)
                logger.info("super_resolution: loaded weights from %s", weights_path)
            self._model.to(device)
            self._model.eval()

    def should_upscale(self, image: Image.Image) -> bool:
        return estimate_dpi(image) < DPI_THRESHOLD

    def upscale(self, image: Image.Image, force: bool = False) -> tuple[Image.Image, bool]:
        if not force and not self.should_upscale(image):
            return image, False

        if self._model is not None and HAS_TORCH:
            return self._upscale_espcn(image), True
        return self._upscale_lanczos(image), True

    def _upscale_espcn(self, image: Image.Image) -> Image.Image:
        gray = image.convert("L")
        arr = np.array(gray, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(self.device)

        with torch.no_grad():
            sr = self._model(tensor)

        sr_arr = sr.squeeze().cpu().numpy()
        sr_arr = np.clip(sr_arr * 255.0, 0, 255).astype(np.uint8)
        sr_gray = Image.fromarray(sr_arr, "L")

        if image.mode == "RGB":
            return image.resize(sr_gray.size, Image.LANCZOS)
        return sr_gray.convert(image.mode)

    def _upscale_lanczos(self, image: Image.Image) -> Image.Image:
        new_w = image.width * self.scale
        new_h = image.height * self.scale
        return image.resize((new_w, new_h), Image.LANCZOS)
