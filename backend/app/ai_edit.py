"""TruthLens Demo AI Studio Engine.

Simulates an AI generation and localized image editing tool.
Embeds TruthLens DCT tile watermarks, attaches IPTC XMP DigitalSourceType,
and generates signed Ed25519 provenance manifests.
"""

from __future__ import annotations

import glob
import io
import math
import os
import urllib.request
import urllib.parse
from typing import Tuple, List, Optional, Dict, Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

from app.watermark import embed_watermark, DEFAULT_BASE_STRENGTH, TILE_SIZE
from app.metadata import embed_metadata, IPTC_TRAINED_ALGORITHMIC, IPTC_COMPOSITE_ALGORITHMIC
from app.provenance import create_manifest


def fetch_pollinations_image(prompt: str, seed: int = 42, timeout: int = 12) -> Optional[Image.Image]:
    """Fetch an AI-generated image from Pollinations.ai based on prompt."""
    try:
        clean_prompt = prompt.strip() or "A scenic photographic scene"
        encoded = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true&seed={seed}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (TruthLens AI Studio; https://truthlens-yihz.onrender.com/)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            return img.resize((512, 512), Image.Resampling.LANCZOS)
    except Exception:
        # Expected in offline/sandbox environments; fallback smoothly
        return None


def generate_synthetic_scene(width: int = 512, height: int = 512, seed: int = 42, prompt: str = "") -> Image.Image:
    """Generate a high-detail procedural photographic scene.

    Creates realistic natural gradient layers tailored to prompt themes:
    nature/landscape, cyberpunk/neon, warm sunset, or twilight mountains.
    """
    arr = np.zeros((height, width, 3), dtype=np.float32)
    rng = np.random.RandomState(seed)
    p_lower = prompt.lower()

    is_cyberpunk = any(k in p_lower for k in ["cyber", "neon", "future", "sci-fi", "robot"])
    is_warm = any(k in p_lower for k in ["sunset", "sunrise", "golden", "autumn", "fall", "dog", "portrait"])

    for y in range(height):
        for x in range(width):
            ratio = y / height
            if is_cyberpunk:
                # Deep neon darks with vibrant cyan and violet gradients
                r = 255 * (0.15 * (1 - ratio) + 0.65 * ratio)
                g = 255 * (0.05 * (1 - ratio) + 0.25 * ratio)
                b = 255 * (0.45 * (1 - ratio) + 0.90 * ratio)
            elif is_warm:
                # Warm golden hour gradient
                r = 255 * (0.95 * (1 - ratio) + 0.35 * ratio)
                g = 255 * (0.55 * (1 - ratio) + 0.20 * ratio)
                b = 255 * (0.25 * (1 - ratio) + 0.45 * ratio)
            else:
                # Sky twilight gradient
                r = 255 * (0.85 * (1 - ratio) + 0.20 * ratio)
                g = 255 * (0.45 * (1 - ratio) + 0.15 * ratio)
                b = 255 * (0.65 * (1 - ratio) + 0.40 * ratio)

            # Mountain silhouette or structural geometry
            m1 = int(260 + 50 * math.sin(x / 45.0) + 25 * math.cos(x / 20.0))
            if y > m1:
                r, g, b = 30 + (y - m1) * 0.15, 25 + (y - m1) * 0.15, 45 + (y - m1) * 0.2

            # Foreground reflection with ripples
            water_line = 360
            if y > water_line:
                ripple = math.sin((x + y * 2) / 8.0) * 15
                r = max(0, min(255, r * 0.7 + ripple))
                g = max(0, min(255, g * 0.6 + ripple))
                b = max(0, min(255, b * 0.85 + ripple * 1.5))

            arr[y, x] = [r, g, b]

    # Glowing focal point (sun / neon orb)
    cx, cy = int(width * 0.65), int(height * 0.40)
    for y in range(max(0, cy - 60), min(height, cy + 60)):
        for x in range(max(0, cx - 60), min(width, cx + 60)):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < 50:
                glow = (1.0 - dist / 50.0) ** 1.5
                if is_cyberpunk:
                    arr[y, x, 0] = min(255, arr[y, x, 0] + 50 * glow)
                    arr[y, x, 1] = min(255, arr[y, x, 1] + 200 * glow)
                    arr[y, x, 2] = min(255, arr[y, x, 2] + 240 * glow)
                elif is_warm:
                    arr[y, x, 0] = min(255, arr[y, x, 0] + 200 * glow)
                    arr[y, x, 1] = min(255, arr[y, x, 1] + 160 * glow)
                    arr[y, x, 2] = min(255, arr[y, x, 2] + 40 * glow)
                else:
                    arr[y, x, 0] = min(255, arr[y, x, 0] + 160 * glow)
                    arr[y, x, 1] = min(255, arr[y, x, 1] + 120 * glow)
                    arr[y, x, 2] = min(255, arr[y, x, 2] + 40 * glow)

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img


def generate_ai_image(
    prompt: str = "A scenic autumn university campus at sunset",
    seed: int = 42,
    base_image: Optional[Image.Image] = None
) -> Tuple[Image.Image, bytes, Dict[str, Any]]:
    """Simulate an AI generator creating an image, fully watermarked with signed provenance.

    Args:
        prompt: User generation prompt.
        seed: Random seed.
        base_image: Optional pre-loaded PIL Image to use as canvas.

    Returns:
        Tuple of (watermarked_image, encoded_bytes, manifest_dict).
    """
    if base_image is not None:
        img = base_image.convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)
    else:
        # 1. Attempt real AI generation using Pollinations AI (works in production deployment on Render)
        fetched = fetch_pollinations_image(prompt=prompt, seed=seed, timeout=12)
        if fetched is not None:
            img = fetched
        else:
            # 2. Check if samples exist to use rich photographic base
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            samples = sorted(glob.glob(os.path.join(root_dir, "samples", "*.jpg"))) or sorted(glob.glob("samples/*.jpg"))
            if samples:
                idx = seed % len(samples)
                img = Image.open(samples[idx]).convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)
            else:
                img = generate_synthetic_scene(512, 512, seed=seed, prompt=prompt)

    # Apply fully marked tile watermark (all tiles marked)
    watermarked = embed_watermark(img, tile_mask=None, base=DEFAULT_BASE_STRENGTH)

    # Create signed Ed25519 provenance manifest
    manifest = create_manifest(
        image=watermarked,
        action="generated",
        edited_tiles=None,
        tool_name=f"TruthLens AI Studio (prompt: '{prompt[:40]}')"
    )

    import json
    manifest_json_str = json.dumps(manifest)

    # Embed IPTC XMP and provenance payload into bytes
    img_bytes = embed_metadata(
        image=watermarked,
        digital_source_type=IPTC_TRAINED_ALGORITHMIC,
        provenance_json_str=manifest_json_str,
        output_format="PNG"
    )

    return watermarked, img_bytes, manifest


def edit_ai_region(
    image: Image.Image,
    box: Tuple[int, int, int, int],
    edit_style: str = "cyberpunk"
) -> Tuple[Image.Image, bytes, Dict[str, Any], List[Tuple[int, int]]]:
    """Simulate a targeted AI region edit (inpaint / neural filter).

    Marks ONLY the tiles covering the edited region, leaving other tiles untouched.
    Adds IPTC compositeWithTrainedAlgorithmicMedia XMP and signed provenance.

    Args:
        image: Original PIL Image.
        box: (x1, y1, x2, y2) pixel bounding box.
        edit_style: Type of visual transformation.

    Returns:
        Tuple of (edited_watermarked_image, encoded_bytes, manifest_dict, edited_tile_coords).
    """
    img_rgb = image.convert("RGB")
    W, H = img_rgb.size

    x1, y1, x2, y2 = box
    x1, x2 = max(0, min(x1, x2)), min(W, max(x1, x2))
    y1, y2 = max(0, min(y1, y2)), min(H, max(y1, y2))

    # Ensure box has minimum size
    if x2 - x1 < 10:
        x2 = min(W, x1 + 64)
    if y2 - y1 < 10:
        y2 = min(H, y1 + 64)

    # 1. Apply visible visual transformation inside box
    edited_np = np.array(img_rgb, dtype=np.float32)
    roi = edited_np[y1:y2, x1:x2]

    if edit_style == "cyberpunk":
        # Boost contrast, shift tones toward vibrant magenta and cyan
        roi[:, :, 0] = np.clip(roi[:, :, 0] * 1.35 + 25, 0, 255)
        roi[:, :, 1] = np.clip(roi[:, :, 1] * 0.85, 0, 255)
        roi[:, :, 2] = np.clip(roi[:, :, 2] * 1.45 + 30, 0, 255)
    elif edit_style == "golden_glow":
        # Warm golden solar glow
        roi[:, :, 0] = np.clip(roi[:, :, 0] * 1.30 + 35, 0, 255)
        roi[:, :, 1] = np.clip(roi[:, :, 1] * 1.15 + 20, 0, 255)
        roi[:, :, 2] = np.clip(roi[:, :, 2] * 0.70, 0, 255)
    else:
        # High-saturation artistic stylization
        mean_lum = 0.299 * roi[:, :, 0] + 0.587 * roi[:, :, 1] + 0.114 * roi[:, :, 2]
        roi[:, :, 0] = np.clip(mean_lum * 1.25 + 20, 0, 255)
        roi[:, :, 1] = np.clip(mean_lum * 0.95 + 10, 0, 255)
        roi[:, :, 2] = np.clip(mean_lum * 1.40 + 30, 0, 255)

    edited_np[y1:y2, x1:x2] = roi
    visually_edited_img = Image.fromarray(np.clip(edited_np, 0, 255).astype(np.uint8))

    # 2. Compute overlapping 64x64 tiles
    n_ty = H // TILE_SIZE
    n_tx = W // TILE_SIZE
    tile_mask = np.zeros((n_ty, n_tx), dtype=bool)

    ty_min = max(0, y1 // TILE_SIZE)
    ty_max = min(n_ty - 1, (y2 - 1) // TILE_SIZE)
    tx_min = max(0, x1 // TILE_SIZE)
    tx_max = min(n_tx - 1, (x2 - 1) // TILE_SIZE)

    edited_tiles: List[Tuple[int, int]] = []
    for ty in range(ty_min, ty_max + 1):
        for tx in range(tx_min, tx_max + 1):
            tile_mask[ty, tx] = True
            edited_tiles.append((ty, tx))

    # 3. Watermark ONLY the marked tiles with robust strength (PSNR >= 41.5 dB)
    watermarked = embed_watermark(visually_edited_img, tile_mask=tile_mask, base=6.5)

    # 4. Create signed Ed25519 provenance manifest
    manifest = create_manifest(
        image=watermarked,
        action="edited",
        edited_tiles=edited_tiles,
        tool_name=f"TruthLens AI Studio (region {box})"
    )

    import json
    manifest_json_str = json.dumps(manifest)

    # 5. Embed IPTC compositeWithTrainedAlgorithmicMedia XMP
    img_bytes = embed_metadata(
        image=watermarked,
        digital_source_type=IPTC_COMPOSITE_ALGORITHMIC,
        provenance_json_str=manifest_json_str,
        output_format="PNG"
    )

    return watermarked, img_bytes, manifest, edited_tiles
