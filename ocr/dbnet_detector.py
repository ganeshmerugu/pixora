"""DBNet (Differentiable Binarization) text detector.

Architecture:
  Input Image -> ResNet-18 + FPN -> Probability Map (P) + Threshold Map (T)
  -> Differentiable Binarization: B_hat = sigmoid(k * (P - T))
  -> Connected Components -> Vatti Polygon Expansion -> Bounding Boxes

Loss:
  L = L_s(P,Y) + alpha * L_b(B_hat,Y) + beta * L_t(T,T*)

Requires PyTorch. Falls back to morphological detection when unavailable.
"""
from __future__ import annotations
import io
import logging
import uuid
from typing import Any

import numpy as np
from PIL import Image

from pixora.models.document import BoundingBox

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


DB_AMPLIFICATION_K = 50
SHRINK_RATIO = 0.4
MIN_BOX_SCORE = 0.5
MIN_BOX_SIZE = 5
PROB_THRESHOLD = 0.3


# -- FPN Neck --


if HAS_TORCH:

    class _FPN(nn.Module):
        def __init__(self, in_channels_list: list[int], out_channels: int = 256):
            super().__init__()
            self.lateral_convs = nn.ModuleList([
                nn.Conv2d(c, out_channels, 1) for c in in_channels_list
            ])
            self.smooth_convs = nn.ModuleList([
                nn.Conv2d(out_channels, out_channels, 3, padding=1) for _ in in_channels_list
            ])
            self.out_channels = out_channels

        def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
            laterals = [conv(f) for conv, f in zip(self.lateral_convs, features)]

            for i in range(len(laterals) - 2, -1, -1):
                h, w = laterals[i].shape[2:]
                laterals[i] = laterals[i] + F.interpolate(
                    laterals[i + 1], size=(h, w), mode="bilinear", align_corners=False,
                )

            outs = [conv(l) for conv, l in zip(self.smooth_convs, laterals)]

            target_h, target_w = outs[0].shape[2:]
            resized = [
                F.interpolate(o, size=(target_h, target_w), mode="bilinear", align_corners=False)
                for o in outs
            ]
            return torch.cat(resized, dim=1)


    class _DBHead(nn.Module):
        def __init__(self, in_channels: int):
            super().__init__()
            self.prob_head = nn.Sequential(
                nn.Conv2d(in_channels, 64, 3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(64, 64, 2, stride=2),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(64, 1, 2, stride=2),
                nn.Sigmoid(),
            )
            self.thresh_head = nn.Sequential(
                nn.Conv2d(in_channels, 64, 3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(64, 64, 2, stride=2),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(64, 1, 2, stride=2),
                nn.Sigmoid(),
            )

        def forward(self, fused: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            prob = self.prob_head(fused)
            thresh = self.thresh_head(fused)
            binary = torch.sigmoid(DB_AMPLIFICATION_K * (prob - thresh))
            return prob, thresh, binary


    class DBNet(nn.Module):
        def __init__(self):
            super().__init__()
            from torchvision.models import resnet18

            backbone = resnet18(weights=None)
            self.layer0 = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu, backbone.maxpool)
            self.layer1 = backbone.layer1  # 64 ch, /4
            self.layer2 = backbone.layer2  # 128 ch, /8
            self.layer3 = backbone.layer3  # 256 ch, /16
            self.layer4 = backbone.layer4  # 512 ch, /32

            self.fpn = _FPN([64, 128, 256, 512], out_channels=64)
            self.head = _DBHead(in_channels=64 * 4)

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            c1 = self.layer1(self.layer0(x))
            c2 = self.layer2(c1)
            c3 = self.layer3(c2)
            c4 = self.layer4(c3)

            fused = self.fpn([c1, c2, c3, c4])

            prob, thresh, binary = self.head(fused)
            return prob, thresh, binary


    class DBNetLoss(nn.Module):
        def __init__(self, alpha: float = 1.0, beta: float = 10.0):
            super().__init__()
            self.alpha = alpha
            self.beta = beta

        def forward(
            self,
            prob: torch.Tensor,
            thresh: torch.Tensor,
            binary: torch.Tensor,
            gt_prob: torch.Tensor,
            gt_thresh: torch.Tensor,
        ) -> torch.Tensor:
            loss_prob = F.binary_cross_entropy(prob.squeeze(1), gt_prob)
            loss_binary = F.binary_cross_entropy(binary.squeeze(1), gt_prob)
            loss_thresh = F.smooth_l1_loss(thresh.squeeze(1), gt_thresh)
            return loss_prob + self.alpha * loss_binary + self.beta * loss_thresh


# -- Vatti Polygon Expansion --


def vatti_expand_polygon(contour: np.ndarray, ratio: float = SHRINK_RATIO) -> np.ndarray:
    if not HAS_CV2 or len(contour) < 3:
        return contour

    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0:
        return contour

    d = area * (1 - ratio * ratio) / perimeter

    contour_f = contour.astype(np.float64).reshape(-1, 2)
    n = len(contour_f)
    expanded = np.zeros_like(contour_f)

    for i in range(n):
        p_prev = contour_f[(i - 1) % n]
        p_curr = contour_f[i]
        p_next = contour_f[(i + 1) % n]

        v1 = p_prev - p_curr
        v2 = p_next - p_curr

        len1 = np.linalg.norm(v1)
        len2 = np.linalg.norm(v2)
        if len1 < 1e-6 or len2 < 1e-6:
            expanded[i] = p_curr
            continue

        n1 = np.array([-v1[1], v1[0]]) / len1
        n2 = np.array([-v2[1], v2[0]]) / len2

        bisector = n1 + n2
        bisector_len = np.linalg.norm(bisector)
        if bisector_len < 1e-6:
            expanded[i] = p_curr + d * n1
        else:
            bisector = bisector / bisector_len
            expanded[i] = p_curr + d * bisector

    return expanded.reshape(-1, 1, 2).astype(np.int32)


# -- Detector Class --


class DBNetDetector:
    def __init__(self, weights_path: str | None = None, device: str = "cpu"):
        if not HAS_TORCH:
            self.model = None
            self.device = "cpu"
            return

        self.device = device
        self.model = DBNet()

        if weights_path:
            state = torch.load(weights_path, map_location=device, weights_only=True)
            self.model.load_state_dict(state)
            logger.info("dbnet: loaded weights from %s", weights_path)

        self.model.to(device)
        self.model.eval()

    def detect(
        self,
        image: Image.Image | bytes,
        page_number: int = 1,
    ) -> list[dict[str, Any]]:
        if isinstance(image, bytes):
            image = Image.open(io.BytesIO(image)).convert("RGB")

        if not HAS_TORCH or self.model is None:
            return self._fallback_detect(image, page_number)

        orig_w, orig_h = image.size
        resized = image.resize((640, 640))
        arr = np.array(resized).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prob, thresh, binary = self.model(tensor)

        prob_map = prob.squeeze().cpu().numpy()
        binary_map = (binary.squeeze().cpu().numpy() > PROB_THRESHOLD).astype(np.uint8) * 255

        boxes = self._extract_boxes(binary_map, prob_map, orig_w, orig_h, page_number)
        return boxes

    def _extract_boxes(
        self,
        binary_map: np.ndarray,
        prob_map: np.ndarray,
        orig_w: int,
        orig_h: int,
        page_number: int,
    ) -> list[dict[str, Any]]:
        if not HAS_CV2:
            return []

        h_map, w_map = binary_map.shape
        contours, _ = cv2.findContours(binary_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        results: list[dict[str, Any]] = []
        scale_x = orig_w / w_map
        scale_y = orig_h / h_map

        for contour in contours:
            if len(contour) < 3:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if w < MIN_BOX_SIZE or h < MIN_BOX_SIZE:
                continue

            mask = np.zeros_like(prob_map)
            cv2.drawContours(mask, [contour], -1, 1.0, -1)
            score = float((prob_map * mask).sum() / max(mask.sum(), 1))
            if score < MIN_BOX_SCORE:
                continue

            expanded = vatti_expand_polygon(contour, SHRINK_RATIO)
            ex, ey, ew, eh = cv2.boundingRect(expanded)

            results.append({
                "box_id": f"db_{page_number}_{uuid.uuid4().hex[:8]}",
                "bbox": BoundingBox(
                    x=round(ex * scale_x),
                    y=round(ey * scale_y),
                    width=round(ew * scale_x),
                    height=round(eh * scale_y),
                    page=page_number,
                ),
                "confidence": round(score, 4),
                "polygon": (expanded.reshape(-1, 2) * [scale_x, scale_y]).astype(int).tolist(),
            })

        results.sort(key=lambda r: (r["bbox"]["y"], r["bbox"]["x"]))
        return results

    def _fallback_detect(
        self, image: Image.Image, page_number: int,
    ) -> list[dict[str, Any]]:
        if not HAS_CV2:
            w, h = image.size
            return [{
                "box_id": f"db_{page_number}_fallback",
                "bbox": BoundingBox(x=0, y=0, width=float(w), height=float(h), page=page_number),
                "confidence": 0.5,
            }]

        arr = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 8))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h_img, w_img = gray.shape
        min_area = w_img * h_img * 0.002
        results: list[dict[str, Any]] = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < min_area:
                continue
            results.append({
                "box_id": f"db_{page_number}_{uuid.uuid4().hex[:8]}",
                "bbox": BoundingBox(x=float(x), y=float(y), width=float(w), height=float(h), page=page_number),
                "confidence": 0.7,
            })

        results.sort(key=lambda r: (r["bbox"]["y"], r["bbox"]["x"]))
        return results
