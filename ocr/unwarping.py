"""Document unwarping via Thin-Plate Spline (TPS) transformation.

For curved or folded documents: detects control points on text lines,
computes TPS coefficients, and applies the warp to flatten the image.

TPS kernel: U(r) = r^2 * log(r)
The transformation solves: [K P; P^T 0] * [w; a] = [v; 0]
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

MIN_CONTROL_POINTS = 6
GRID_ROWS = 4
GRID_COLS = 6


def _tps_kernel(r: np.ndarray) -> np.ndarray:
    result = np.zeros_like(r)
    mask = r > 0
    result[mask] = r[mask] ** 2 * np.log(r[mask])
    return result


def _compute_tps_coefficients(
    source_points: np.ndarray,
    target_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Solve the TPS linear system for x and y displacements.

    Returns (W, A) where W is (N, 2) non-affine weights and A is (3, 2) affine part.
    """
    n = len(source_points)

    dists = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dists[i, j] = np.sqrt(np.sum((source_points[i] - source_points[j]) ** 2))

    K = _tps_kernel(dists)

    P = np.ones((n, 3))
    P[:, 1:] = source_points

    L = np.zeros((n + 3, n + 3))
    L[:n, :n] = K
    L[:n, n:] = P
    L[n:, :n] = P.T

    reg = 1e-3
    L[:n, :n] += reg * np.eye(n)

    V = np.zeros((n + 3, 2))
    V[:n] = target_points

    try:
        params = np.linalg.solve(L, V)
    except np.linalg.LinAlgError:
        params = np.linalg.lstsq(L, V, rcond=None)[0]

    W = params[:n]
    A = params[n:]

    return W, A


def _apply_tps(
    image: np.ndarray,
    source_points: np.ndarray,
    W: np.ndarray,
    A: np.ndarray,
    output_size: tuple[int, int] | None = None,
) -> np.ndarray:
    h, w = image.shape[:2]
    out_h, out_w = output_size or (h, w)

    ys, xs = np.mgrid[0:out_h, 0:out_w].astype(np.float64)
    grid = np.stack([xs.ravel(), ys.ravel()], axis=1)

    n = len(source_points)
    dists = np.zeros((len(grid), n))
    for i in range(n):
        dx = grid[:, 0] - source_points[i, 0]
        dy = grid[:, 1] - source_points[i, 1]
        dists[:, i] = np.sqrt(dx ** 2 + dy ** 2)

    K = _tps_kernel(dists)

    P = np.ones((len(grid), 3))
    P[:, 1:] = grid

    mapped = K @ W + P @ A

    map_x = mapped[:, 0].reshape(out_h, out_w).astype(np.float32)
    map_y = mapped[:, 1].reshape(out_h, out_w).astype(np.float32)

    map_x = np.clip(map_x, 0, w - 1)
    map_y = np.clip(map_y, 0, h - 1)

    result = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderValue=(255, 255, 255))
    return result


class DocumentUnwarper:
    def __init__(self, grid_rows: int = GRID_ROWS, grid_cols: int = GRID_COLS):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

    def unwarp(self, image: Image.Image) -> tuple[Image.Image, list[tuple[float, float]]]:
        if not HAS_CV2:
            return image, []

        arr = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        source_pts, target_pts = self._detect_control_points(gray, w, h)

        if len(source_pts) < MIN_CONTROL_POINTS:
            logger.debug("unwarping: only %d control points, skipping", len(source_pts))
            return image, []

        W, A = _compute_tps_coefficients(source_pts, target_pts)
        result = _apply_tps(arr, source_pts, W, A, (h, w))

        control_list = [(float(p[0]), float(p[1])) for p in source_pts]
        return Image.fromarray(result), control_list

    def _detect_control_points(
        self, gray: np.ndarray, w: int, h: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        source_pts: list[list[float]] = []
        target_pts: list[list[float]] = []

        row_step = h // (self.grid_rows + 1)
        col_step = w // (self.grid_cols + 1)

        for r in range(1, self.grid_rows + 1):
            y_nominal = r * row_step

            for c in range(1, self.grid_cols + 1):
                x_nominal = c * col_step

                y_actual = self._find_text_baseline(binary, x_nominal, y_nominal, h)

                source_pts.append([float(x_nominal), float(y_actual)])
                target_pts.append([float(x_nominal), float(y_nominal)])

        return np.array(source_pts), np.array(target_pts)

    def _find_text_baseline(
        self, binary: np.ndarray, x: int, y_center: int, h: int,
    ) -> float:
        search_range = h // 8
        y_start = max(0, y_center - search_range)
        y_end = min(h, y_center + search_range)

        col_width = 20
        x_start = max(0, x - col_width)
        x_end = min(binary.shape[1], x + col_width)

        strip = binary[y_start:y_end, x_start:x_end]
        proj = np.sum(strip > 0, axis=1).astype(np.float64)

        if np.max(proj) < 5:
            return float(y_center)

        peak_idx = int(np.argmax(proj))
        return float(y_start + peak_idx)
