from __future__ import annotations
import logging
from typing import Any
from typing_extensions import Required, TypedDict
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
import io

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG": "png",
    b"GIF8": "gif",
    b"BM": "bmp",
    b"II\x2a\x00": "tiff_le",
    b"MM\x00\x2a": "tiff_be",
    b"RIFF": "webp",
}

MIN_IMAGE_DIM = 10
MAX_IMAGE_PIXELS = 50_000_000


class ImageValidationResult(TypedDict, total=False):
    valid: Required[bool]
    format_detected: str
    width: int
    height: int
    reason: str


def validate_image_bytes(image_bytes: bytes) -> ImageValidationResult:
    if not image_bytes or len(image_bytes) < 8:
        return ImageValidationResult(valid=False, reason="empty_or_too_small")

    detected = "unknown"
    for magic, fmt in IMAGE_MAGIC_BYTES.items():
        if image_bytes[:len(magic)] == magic:
            detected = fmt
            break

    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
    except Exception as exc:
        return ImageValidationResult(valid=False, format_detected=detected, reason=f"corrupt: {exc}")

    if w < MIN_IMAGE_DIM or h < MIN_IMAGE_DIM:
        return ImageValidationResult(valid=False, format_detected=detected, width=w, height=h, reason="too_small")

    if w * h > MAX_IMAGE_PIXELS:
        return ImageValidationResult(valid=False, format_detected=detected, width=w, height=h, reason="too_large")

    return ImageValidationResult(valid=True, format_detected=detected, width=w, height=h)


def fix_exif_orientation(image: Image.Image) -> tuple[Image.Image, bool]:
    try:
        corrected = ImageOps.exif_transpose(image)
        if corrected is not image:
            return corrected, True
        return image, False
    except Exception:
        return image, False


def _is_blank_image(image: Image.Image, threshold: float = 0.98) -> bool:
    gray = image.convert("L")
    arr = np.array(gray)
    total = arr.size
    if total == 0:
        return True
    white_ratio = np.count_nonzero(arr > 250) / total
    black_ratio = np.count_nonzero(arr < 5) / total
    return white_ratio > threshold or black_ratio > threshold


class PreprocessingConfig(TypedDict, total=False):
    noise_removal: bool
    binarization: bool
    adaptive_binarization: bool
    deskew: bool
    contrast: bool
    camera_correction: bool
    target_dpi: int
    sharpen: bool
    border_removal: bool
    metadata: dict[str, Any]


class PreprocessedImage(TypedDict, total=False):
    image: Required[Image.Image]
    transforms_applied: list[str]
    original_size: tuple[int, int]
    skew_angle: float
    estimated_dpi: int
    metadata: dict[str, Any]


DEFAULT_CONFIG = PreprocessingConfig(
    noise_removal=True,
    binarization=False,
    adaptive_binarization=True,
    deskew=True,
    contrast=True,
    camera_correction=False,
    target_dpi=300,
    sharpen=True,
    border_removal=True,
)


def _pil_to_cv(image: Image.Image) -> np.ndarray:
    if image.mode == "L":
        return np.array(image)
    rgb = image.convert("RGB")
    return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def _cv_to_pil(arr: np.ndarray) -> Image.Image:
    if len(arr.shape) == 2:
        return Image.fromarray(arr, "L").convert("RGB")
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


class PreprocessingPipeline:
    def process(self, image: Image.Image, config: PreprocessingConfig | None = None) -> PreprocessedImage:
        config = config or DEFAULT_CONFIG
        transforms: list[str] = []
        original_size = image.size
        skew_angle = 0.0

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image, exif_fixed = fix_exif_orientation(image)
        if exif_fixed:
            transforms.append("exif_orientation")

        if _is_blank_image(image):
            logger.warning("preprocessing: detected blank/near-blank image")

        if config.get("target_dpi", 300) and HAS_CV2:
            image = self._scale_to_dpi(image, config.get("target_dpi", 300))
            transforms.append("dpi_scaling")

        if config.get("noise_removal", True):
            image = self._remove_noise(image)
            transforms.append("noise_removal")

        if config.get("contrast", True):
            image = self._enhance_contrast(image)
            transforms.append("contrast")

        if config.get("sharpen", True):
            image = self._sharpen(image)
            transforms.append("sharpen")

        if config.get("deskew", True) and HAS_CV2:
            image, skew_angle = self._deskew(image)
            if abs(skew_angle) > 0.1:
                transforms.append("deskew")

        if config.get("adaptive_binarization", True) and HAS_CV2:
            image = self._adaptive_binarize(image)
            transforms.append("adaptive_binarization")
        elif config.get("binarization", False):
            image = self._otsu_binarize(image)
            transforms.append("binarization")

        if config.get("border_removal", True) and HAS_CV2:
            image = self._remove_borders(image)
            transforms.append("border_removal")

        if config.get("camera_correction", False) and HAS_CV2:
            image = self._correct_perspective(image)
            transforms.append("camera_correction")

        if image.mode != "RGB":
            image = image.convert("RGB")

        return PreprocessedImage(
            image=image,
            transforms_applied=transforms,
            original_size=original_size,
            skew_angle=skew_angle,
            estimated_dpi=config.get("target_dpi", 300),
        )

    def _scale_to_dpi(self, image: Image.Image, target_dpi: int) -> Image.Image:
        current_dpi = image.info.get("dpi", (72, 72))
        if isinstance(current_dpi, tuple):
            current_dpi = current_dpi[0]
        if current_dpi >= target_dpi:
            return image
        scale = target_dpi / max(current_dpi, 1)
        new_size = (int(image.width * scale), int(image.height * scale))
        return image.resize(new_size, Image.LANCZOS)

    def _remove_noise(self, image: Image.Image) -> Image.Image:
        if HAS_CV2:
            arr = _pil_to_cv(image)
            if len(arr.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(arr, None, 10, 10, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(arr, None, 10, 7, 21)
            return _cv_to_pil(denoised)
        return image.filter(ImageFilter.MedianFilter(size=3))

    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        if HAS_CV2:
            arr = _pil_to_cv(image)
            if len(arr.shape) == 3:
                lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
                l_channel = lab[:, :, 0]
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(l_channel)
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                result = clahe.apply(arr)
            return _cv_to_pil(result)
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(1.5)

    def _sharpen(self, image: Image.Image) -> Image.Image:
        if HAS_CV2:
            arr = _pil_to_cv(image)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
            sharpened = cv2.filter2D(arr, -1, kernel)
            return _cv_to_pil(sharpened)
        return image.filter(ImageFilter.SHARPEN)

    def _deskew(self, image: Image.Image) -> tuple[Image.Image, float]:
        arr = _pil_to_cv(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)

        if lines is None or len(lines) == 0:
            return image, 0.0

        angles = []
        for line in lines:
            pts = line.flatten()
            if len(pts) < 4:
                continue
            x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) > 0:
                angle = np.degrees(np.arctan2(dy, dx))
                if abs(angle) < 45:
                    angles.append(angle)

        if not angles:
            return image, 0.0

        median_angle = float(np.median(angles))

        if abs(median_angle) < 0.5:
            return image, median_angle

        h, w = arr.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(arr, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return _cv_to_pil(rotated), median_angle

    def _adaptive_binarize(self, image: Image.Image) -> Image.Image:
        arr = _pil_to_cv(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
        return _cv_to_pil(binary)

    def _otsu_binarize(self, image: Image.Image) -> Image.Image:
        if HAS_CV2:
            arr = _pil_to_cv(image)
            gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return _cv_to_pil(binary)
        gray = ImageOps.grayscale(image)
        return gray.point(lambda p: 255 if p > 128 else 0, "1").convert("RGB")

    def _remove_borders(self, image: Image.Image) -> Image.Image:
        arr = _pil_to_cv(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
        contours, _ = cv2.findContours(cv2.bitwise_not(gray), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return image

        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)

        img_h, img_w = gray.shape[:2]
        margin = 5
        if w > img_w * 0.5 and h > img_h * 0.5:
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img_w - x, w + 2 * margin)
            h = min(img_h - y, h + 2 * margin)
            cropped = arr[y:y+h, x:x+w]
            return _cv_to_pil(cropped)

        return image

    def _correct_perspective(self, image: Image.Image) -> Image.Image:
        arr = _pil_to_cv(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return image

        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

        if len(approx) != 4:
            return image

        pts = approx.reshape(4, 2).astype(np.float32)
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect

        width_a = np.sqrt((br[0] - bl[0])**2 + (br[1] - bl[1])**2)
        width_b = np.sqrt((tr[0] - tl[0])**2 + (tr[1] - tl[1])**2)
        max_width = int(max(width_a, width_b))

        height_a = np.sqrt((tr[0] - br[0])**2 + (tr[1] - br[1])**2)
        height_b = np.sqrt((tl[0] - bl[0])**2 + (tl[1] - bl[1])**2)
        max_height = int(max(height_a, height_b))

        dst = np.array([[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]], dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(arr, matrix, (max_width, max_height))
        return _cv_to_pil(warped)

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        return rect

    def image_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        buf = io.BytesIO()
        image.save(buf, format=format)
        return buf.getvalue()
