"""TruthLens Adversarial Attack Suite.

Implements realistic adversarial transformations: metadata stripping / screenshot,
JPEG compression at varying qualities, spatial crops with odd pixel offsets,
brightness shifts, and image resampling.
"""

from __future__ import annotations

import io
from typing import Tuple, Dict, Any, Callable
from PIL import Image, ImageEnhance

from app.metadata import strip_metadata


def attack_none(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Identity transformation (no attack)."""
    return img.copy(), img_bytes


def attack_screenshot_strip(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Emulate desktop screenshot / social media upload by stripping all metadata."""
    stripped_bytes = strip_metadata(img_bytes, output_format="PNG")
    out_img = Image.open(io.BytesIO(stripped_bytes)).convert("RGB")
    return out_img, stripped_bytes


def attack_jpeg_q90(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply high-quality JPEG compression (quality 90)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    data = buf.getvalue()
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_jpeg_q75(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply standard web JPEG compression (quality 75)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    data = buf.getvalue()
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_jpeg_q50(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply aggressive JPEG compression (quality 50)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=50)
    data = buf.getvalue()
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_crop_10_odd(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Crop ~10% total dimensions with an odd pixel offset (disrupting 8x8 block grid)."""
    W, H = img.size
    # Odd offsets: left=7, top=11
    # Right border=W-19, Bottom border=H-23
    cropped = img.convert("RGB").crop((7, 11, max(64, W - 19), max(64, H - 23)))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    data = buf.getvalue()
    return cropped, data


def attack_crop_jpeg_q75(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Compound attack: odd pixel crop followed by JPEG q75 compression."""
    cropped, _ = attack_crop_10_odd(img, img_bytes)
    return attack_jpeg_q75(cropped, b"")


def attack_brightness_plus_10(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Increase luminance brightness by 10%."""
    enhanced = ImageEnhance.Brightness(img.convert("RGB")).enhance(1.1)
    buf = io.BytesIO()
    enhanced.save(buf, format="PNG")
    data = buf.getvalue()
    return enhanced, data


def attack_resize_0_9x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Downsample image to 0.9x scale with Lanczos filtering."""
    W, H = img.size
    new_w = max(64, int(W * 0.9))
    new_h = max(64, int(H * 0.9))
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    data = buf.getvalue()
    return resized, data


def attack_resize_1_5x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Upsample image to 1.5x scale with Lanczos filtering."""
    W, H = img.size
    new_w = int(W * 1.5)
    new_h = int(H * 1.5)
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    data = buf.getvalue()
    return resized, data


ATTACK_REGISTRY: Dict[str, Callable[[Image.Image, bytes], Tuple[Image.Image, bytes]]] = {
    "none": attack_none,
    "screenshot_strip": attack_screenshot_strip,
    "jpeg_q90": attack_jpeg_q90,
    "jpeg_q75": attack_jpeg_q75,
    "jpeg_q50": attack_jpeg_q50,
    "crop_10_odd": attack_crop_10_odd,
    "crop_jpeg_q75": attack_crop_jpeg_q75,
    "brightness_plus_10": attack_brightness_plus_10,
    "resize_0_9x": attack_resize_0_9x,
    "resize_1_5x": attack_resize_1_5x,
}


def apply_attack(
    attack_name: str,
    image: Image.Image,
    image_bytes: bytes
) -> Tuple[Image.Image, bytes]:
    """Apply named attack to image and return modified (image, bytes).

    Args:
        attack_name: Key in ATTACK_REGISTRY.
        image: PIL Image.
        image_bytes: Raw image file bytes.

    Returns:
        Tuple[Image.Image, bytes]: Attacked image and its byte representation.
    """
    if attack_name not in ATTACK_REGISTRY:
        raise ValueError(f"Unknown attack '{attack_name}'. Valid options: {list(ATTACK_REGISTRY.keys())}")
    return ATTACK_REGISTRY[attack_name](image, image_bytes)
