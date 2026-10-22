"""Feature extraction from segmented text regions.

Classical mode: HOG (Histogram of Oriented Gradients) + zoning features.
Deep mode: CNN feature maps from the CRNN backbone.

The CNN backbone processes a region image (resized to 32xW) through
convolutional layers to produce a feature volume F in R^(D x 1 x T),
where T = W/4 is the sequence length and D is channel depth (512).
"""
from __future__ import annotations
import logging
from typing import Any

import numpy as np
from typing_extensions import Required, TypedDict
from PIL import Image

from pixora.ocr.segmenter import SegmentedRegion

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class FeatureSet(TypedDict, total=False):
    mode: Required[str]
    features: dict[str, Any]
    metadata: dict[str, Any]


HOG_CELL_SIZE = 8
HOG_BLOCK_SIZE = 2
HOG_NBINS = 9
ZONE_GRID = (4, 4)
RESIZE_H = 64
RESIZE_W = 128


class FeatureExtractor:
    def __init__(self, source_image: Image.Image | None = None):
        self._source = source_image

    def set_source_image(self, image: Image.Image) -> None:
        self._source = image

    def extract(self, region: SegmentedRegion, mode: str = "engine_internal") -> FeatureSet:
        if mode == "classical":
            return self._extract_classical(region)
        elif mode == "deep":
            return self._extract_deep(region)
        return FeatureSet(mode="engine_internal", features={}, metadata={})

    def _crop_region(self, region: SegmentedRegion) -> np.ndarray | None:
        if self._source is None:
            return None
        bbox = region["bbox"]
        x, y = int(bbox["x"]), int(bbox["y"])
        w, h = int(bbox["width"]), int(bbox["height"])
        if w <= 0 or h <= 0:
            return None
        cropped = self._source.crop((x, y, x + w, y + h))
        return np.array(cropped.convert("L"))

    # -- Classical: HOG + Zoning + Projections --

    def _extract_classical(self, region: SegmentedRegion) -> FeatureSet:
        gray = self._crop_region(region)
        if gray is None or not HAS_CV2:
            return FeatureSet(
                mode="classical",
                features={"type": "hog_zoning", "region_type": region["type"]},
                metadata={"error": "no_image" if gray is None else "no_cv2"},
            )

        resized = cv2.resize(gray, (RESIZE_W, RESIZE_H))

        hog_features = self._compute_hog(resized)
        zone_features = self._compute_zoning(resized)
        projection_features = self._compute_projections(resized)

        combined = np.concatenate([hog_features, zone_features, projection_features])

        return FeatureSet(
            mode="classical",
            features={
                "type": "hog_zoning",
                "region_type": region["type"],
                "vector": combined.tolist(),
                "hog_dim": len(hog_features),
                "zone_dim": len(zone_features),
                "projection_dim": len(projection_features),
                "total_dim": len(combined),
            },
            metadata={
                "resize": (RESIZE_H, RESIZE_W),
                "hog_cells": HOG_CELL_SIZE,
                "hog_bins": HOG_NBINS,
                "zone_grid": ZONE_GRID,
            },
        )

    def _compute_hog(self, gray: np.ndarray) -> np.ndarray:
        """Histogram of Oriented Gradients via Sobel + binning + L2 block normalization."""
        h, w = gray.shape
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        angle = np.arctan2(gy, gx) * (180.0 / np.pi) % 180.0

        cells_y = h // HOG_CELL_SIZE
        cells_x = w // HOG_CELL_SIZE
        histograms = np.zeros((cells_y, cells_x, HOG_NBINS), dtype=np.float64)
        bin_width = 180.0 / HOG_NBINS

        for cy in range(cells_y):
            for cx in range(cells_x):
                y0 = cy * HOG_CELL_SIZE
                x0 = cx * HOG_CELL_SIZE
                cell_mag = magnitude[y0:y0 + HOG_CELL_SIZE, x0:x0 + HOG_CELL_SIZE]
                cell_ang = angle[y0:y0 + HOG_CELL_SIZE, x0:x0 + HOG_CELL_SIZE]

                for b in range(HOG_NBINS):
                    lo = b * bin_width
                    hi = (b + 1) * bin_width
                    mask = (cell_ang >= lo) & (cell_ang < hi)
                    histograms[cy, cx, b] = np.sum(cell_mag[mask])

        blocks_y = cells_y - HOG_BLOCK_SIZE + 1
        blocks_x = cells_x - HOG_BLOCK_SIZE + 1
        if blocks_y <= 0 or blocks_x <= 0:
            flat = histograms.flatten()
            norm = np.linalg.norm(flat) + 1e-6
            return flat / norm

        normalized: list[np.ndarray] = []
        for by in range(blocks_y):
            for bx in range(blocks_x):
                block = histograms[by:by + HOG_BLOCK_SIZE, bx:bx + HOG_BLOCK_SIZE].flatten()
                norm = np.linalg.norm(block) + 1e-6
                normalized.append(block / norm)

        return np.concatenate(normalized)

    def _compute_zoning(self, gray: np.ndarray) -> np.ndarray:
        """Per-zone ink density, horizontal transition density, and stroke count."""
        h, w = gray.shape
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        zones_y, zones_x = ZONE_GRID
        zone_h = h // zones_y
        zone_w = w // zones_x

        features: list[float] = []
        for zy in range(zones_y):
            for zx in range(zones_x):
                zone = binary[zy * zone_h:(zy + 1) * zone_h, zx * zone_w:(zx + 1) * zone_w]
                total_pixels = zone.size
                if total_pixels == 0:
                    features.extend([0.0, 0.0, 0.0])
                    continue

                ink_density = float(np.count_nonzero(zone)) / total_pixels

                transitions = 0
                for row in zone:
                    diffs = np.abs(np.diff(row.astype(np.int16)))
                    transitions += np.count_nonzero(diffs)
                transition_density = transitions / total_pixels

                contours, _ = cv2.findContours(zone, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                stroke_count = len(contours) / max(total_pixels / 100, 1)

                features.extend([ink_density, transition_density, stroke_count])

        return np.array(features, dtype=np.float64)

    def _compute_projections(self, gray: np.ndarray) -> np.ndarray:
        """Normalized horizontal and vertical projection profiles, resampled to fixed length."""
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        horizontal = np.sum(binary > 0, axis=1).astype(np.float64)
        vertical = np.sum(binary > 0, axis=0).astype(np.float64)

        h_max = horizontal.max() if horizontal.max() > 0 else 1.0
        v_max = vertical.max() if vertical.max() > 0 else 1.0
        horizontal /= h_max
        vertical /= v_max

        target_len = 32
        h_proj = np.interp(
            np.linspace(0, len(horizontal) - 1, target_len),
            np.arange(len(horizontal)), horizontal,
        )
        v_proj = np.interp(
            np.linspace(0, len(vertical) - 1, target_len),
            np.arange(len(vertical)), vertical,
        )

        return np.concatenate([h_proj, v_proj])

    # -- Deep: CNN Feature Map (F in R^(D x 1 x T)) --

    def _extract_deep(self, region: SegmentedRegion) -> FeatureSet:
        gray = self._crop_region(region)
        if gray is None:
            return FeatureSet(
                mode="deep",
                features={"type": "cnn_feature_map", "region_type": region["type"]},
                metadata={"error": "no_image"},
            )

        if not HAS_TORCH:
            return FeatureSet(
                mode="deep",
                features={"type": "cnn_feature_map", "region_type": region["type"]},
                metadata={"error": "torch_not_available"},
            )

        rgb = np.stack([gray, gray, gray], axis=-1) if len(gray.shape) == 2 else gray
        image = Image.fromarray(rgb)

        h_orig, w_orig = gray.shape[:2]
        scale = 32.0 / h_orig
        new_w = max(int(w_orig * scale), 1)
        resized = image.resize((new_w, 32))

        arr = np.array(resized).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)

        try:
            from pixora.ocr.crnn_recognizer import CRNN, NUM_CLASSES
            model = CRNN(num_classes=NUM_CLASSES)
            model.eval()

            with torch.no_grad():
                feature_volume = model.cnn(tensor)  # (1, 512, 1, T)

            fv = feature_volume.squeeze().numpy()  # (512, T) or (512,)
            if fv.ndim == 1:
                fv = fv.reshape(-1, 1)

            D, T = fv.shape
            pooled = fv.mean(axis=1)  # global average pooling -> (D,)

            return FeatureSet(
                mode="deep",
                features={
                    "type": "cnn_feature_map",
                    "region_type": region["type"],
                    "vector": pooled.tolist(),
                    "feature_dim": D,
                    "sequence_length": T,
                    "total_dim": len(pooled),
                    "spatial_shape": [D, 1, T],
                },
                metadata={
                    "backbone": "crnn_cnn",
                    "input_size": (32, new_w),
                },
            )
        except Exception as exc:
            logger.warning("features: deep extraction failed: %s", exc)
            return FeatureSet(
                mode="deep",
                features={"type": "cnn_feature_map", "region_type": region["type"]},
                metadata={"error": str(exc)},
            )
