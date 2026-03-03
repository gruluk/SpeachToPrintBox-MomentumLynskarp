"""
Algorithmic pixel art pipeline — no AI generation required.

Steps:
  1. Face detection + crop to face + shoulders (OpenCV Haar cascade)
  2. Normalize: boost contrast, brightness, sharpness
  3. Downscale to PIXEL_ART_SIZE × PIXEL_ART_SIZE using LANCZOS (area averaging)
  4. Color quantize to N_COLORS with Floyd-Steinberg dithering
  5. Draw 1px dark outline at color boundaries
  6. Upscale with nearest-neighbor for chunky pixel look

Output is a square PIL Image (RGB). Caller converts to grayscale if needed.
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# --- Tuning knobs ---
PIXEL_ART_SIZE = 64   # square pixel art canvas (px)
N_COLORS = 20         # palette size — fewer = more stylized, more = more natural
UPSCALE = 6           # 64 × 6 = 384px output
OUTLINE_THRESHOLD = 15  # edge sensitivity (0–255, lower = more outlines)
OUTLINE_DARKEN = 70     # how much to darken outline pixels


def _detect_face_crop(image: Image.Image) -> Image.Image:
    """
    Detect the largest face and return a square crop including forehead + shoulders.
    Falls back to a center square crop if no face is found.
    """
    img_np = np.array(image)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    W, H = image.size

    if len(faces) == 0:
        # No face — fall back to center square crop
        size = min(W, H)
        left = (W - size) // 2
        top = (H - size) // 2
        return image.crop((left, top, left + size, top + size))

    # Pick the largest detected face
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])

    # Expand box: forehead above, shoulders below and to the sides
    pad_top = int(fh * 0.5)
    pad_side = int(fw * 0.6)
    pad_bottom = int(fh * 0.9)

    x1 = max(0, x - pad_side)
    y1 = max(0, y - pad_top)
    x2 = min(W, x + fw + pad_side)
    y2 = min(H, y + fh + pad_bottom)

    # Force to a square around the center of the expanded box
    cw, ch = x2 - x1, y2 - y1
    size = max(cw, ch)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    x1 = max(0, cx - size // 2)
    y1 = max(0, cy - size // 2)
    x2 = min(W, x1 + size)
    y2 = min(H, y1 + size)

    return image.crop((x1, y1, x2, y2))


def _normalize(image: Image.Image) -> Image.Image:
    """Boost contrast, brightness and sharpness before downscaling."""
    image = ImageEnhance.Contrast(image).enhance(1.3)
    image = ImageEnhance.Brightness(image).enhance(1.05)
    image = ImageEnhance.Sharpness(image).enhance(2.0)
    return image


def _add_outline(image: Image.Image) -> Image.Image:
    """Darken pixels that sit on a color boundary — classic sprite outline."""
    edges = image.filter(ImageFilter.FIND_EDGES).convert("L")
    edge_mask = edges.point(lambda p: 255 if p > OUTLINE_THRESHOLD else 0)
    darkened = image.point(lambda p: max(0, p - OUTLINE_DARKEN))
    return Image.composite(darkened, image, edge_mask)


def pixelate(photo: Image.Image) -> Image.Image:
    """Run the full pixel art pipeline and return a square RGB image."""
    photo = photo.convert("RGB")

    # 1. Face detection + crop
    cropped = _detect_face_crop(photo)

    # 2. Normalize
    normalized = _normalize(cropped)

    # 3. Downscale to pixel art resolution (LANCZOS = best area averaging)
    small = normalized.resize((PIXEL_ART_SIZE, PIXEL_ART_SIZE), Image.LANCZOS)

    # 4. Quantize to N_COLORS with Floyd-Steinberg dithering
    quantized = small.quantize(
        colors=N_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    ).convert("RGB")

    # 5. Outline
    outlined = _add_outline(quantized)

    # 6. Upscale with nearest-neighbor — hard pixel edges, no blending
    output_size = PIXEL_ART_SIZE * UPSCALE  # 64 × 6 = 384
    return outlined.resize((output_size, output_size), Image.NEAREST)
