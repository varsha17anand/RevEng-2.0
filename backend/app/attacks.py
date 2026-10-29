"""TruthLens Adversarial Attack Suite.

Implements realistic adversarial transformations: metadata stripping / screenshot,
JPEG compression at varying qualities, spatial crops with odd pixel offsets,
brightness shifts, and image resampling.
"""

from __future__ import annotations

import io
from typing import Tuple, Dict, Any, Callable
from PIL import Image, ImageEnhance

from app.metadata import (
    strip_metadata,
    embed_metadata,
    read_digital_source_type,
    extract_provenance_raw
)


def _save_with_preserved_metadata(
    img: Image.Image,
    original_bytes: bytes,
    output_format: str = "PNG",
    quality: int = 95
) -> bytes:
    """Save image while preserving IPTC XMP and provenance metadata from original_bytes."""
    digital_source = read_digital_source_type(original_bytes)
    prov_str = extract_provenance_raw(original_bytes)

    if digital_source or prov_str:
        return embed_metadata(
            img,
            digital_source_type=digital_source or "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
            provenance_json_str=prov_str,
            output_format=output_format,
            quality=quality
        )

    buf = io.BytesIO()
    if output_format.upper() == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
    else:
        img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def attack_none(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Identity transformation (no attack)."""
    return img.copy(), img_bytes


def attack_screenshot_strip(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Emulate desktop screenshot / social media upload by stripping all metadata."""
    stripped_bytes = strip_metadata(img_bytes, output_format="PNG")
    out_img = Image.open(io.BytesIO(stripped_bytes)).convert("RGB")
    return out_img, stripped_bytes


def attack_jpeg_q90(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply high-quality JPEG compression (quality 90, preserving metadata)."""
    data = _save_with_preserved_metadata(img, img_bytes, output_format="JPEG", quality=90)
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_jpeg_q75(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply standard web JPEG compression (quality 75, preserving metadata)."""
    data = _save_with_preserved_metadata(img, img_bytes, output_format="JPEG", quality=75)
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_jpeg_q50(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Apply aggressive JPEG compression (quality 50, preserving metadata)."""
    data = _save_with_preserved_metadata(img, img_bytes, output_format="JPEG", quality=50)
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_crop_10_odd(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Crop ~10% total dimensions with an odd pixel offset (preserving metadata)."""
    W, H = img.size
    # Odd offsets: left=7, top=11
    # Right border=W-19, Bottom border=H-23
    cropped = img.convert("RGB").crop((7, 11, max(64, W - 19), max(64, H - 23)))
    data = _save_with_preserved_metadata(cropped, img_bytes, output_format="PNG")
    return cropped, data


def attack_crop_jpeg_q75(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Compound attack: odd pixel crop followed by JPEG q75 compression."""
    cropped, _ = attack_crop_10_odd(img, img_bytes)
    data = _save_with_preserved_metadata(cropped, img_bytes, output_format="JPEG", quality=75)
    return Image.open(io.BytesIO(data)).convert("RGB"), data


def attack_brightness_plus_10(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Increase luminance brightness by 10% (preserving metadata)."""
    enhanced = ImageEnhance.Brightness(img.convert("RGB")).enhance(1.1)
    data = _save_with_preserved_metadata(enhanced, img_bytes, output_format="PNG")
    return enhanced, data


def attack_resize_0_9x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Downsample image to 0.9x scale with Lanczos filtering (preserving metadata)."""
    W, H = img.size
    new_w = max(64, int(W * 0.9))
    new_h = max(64, int(H * 0.9))
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    data = _save_with_preserved_metadata(resized, img_bytes, output_format="PNG")
    return resized, data


def attack_resize_1_5x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Upsample image to 1.5x scale with Lanczos filtering (preserving metadata)."""
    W, H = img.size
    new_w = int(W * 1.5)
    new_h = int(H * 1.5)
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    data = _save_with_preserved_metadata(resized, img_bytes, output_format="PNG")
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
