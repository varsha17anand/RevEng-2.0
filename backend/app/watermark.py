"""TruthLens DCT Tile Watermarking Engine.

Implements an orthonormal 2D DCT tile watermark embedded in luminance (Y)
low-to-mid frequency coefficients with texture masking. Survives JPEG compression,
resyncs after arbitrary pixel crops, and detects localized AI modifications.
"""

from __future__ import annotations

import hashlib
import io
from typing import Tuple, Optional

import numpy as np
import scipy.fft
from PIL import Image

# 12 low/mid-frequency DCT coefficients specified in the TruthLens algorithm:
# (0,2),(1,1),(2,0),(3,0),(2,1),(1,2),(0,3),(0,4),(1,3),(2,2),(3,1),(4,0)
COEFF_INDICES = [
    (0, 2), (1, 1), (2, 0),
    (3, 0), (2, 1), (1, 2), (0, 3),
    (0, 4), (1, 3), (2, 2), (3, 1), (4, 0)
]
COEFF_ROWS = np.array([r for r, c in COEFF_INDICES], dtype=np.int64)
COEFF_COLS = np.array([c for r, c in COEFF_INDICES], dtype=np.int64)

DEFAULT_SECRET_KEY = "truthlens-v1-meta-194"
DEFAULT_BASE_STRENGTH = 3.5
DETECTION_THRESHOLD = 4.0
GENERATED_THRESHOLD = 0.25
RESYNC_DETECTION_THRESHOLD = 4.5
TILE_SIZE = 64
BLOCK_SIZE = 8


def get_watermark_pattern(secret_key: str = DEFAULT_SECRET_KEY) -> np.ndarray:
    """Generate the deterministic ±1 watermark pattern of length 12 from secret key.

    Args:
        secret_key: Secret key string used to seed the RNG.

    Returns:
        np.ndarray: Length-12 vector with values in {-1.0, 1.0}.
    """
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big") % (2**32)
    rng = np.random.RandomState(seed)
    return rng.choice([-1.0, 1.0], size=12).astype(np.float32)


def rgb_to_luminance(rgb_array: np.ndarray) -> np.ndarray:
    """Convert RGB float array to ITU-R BT.601 luminance Y.

    Args:
        rgb_array: Image array of shape (H, W, 3) in [0, 255].

    Returns:
        np.ndarray: 2D Luminance array of shape (H, W).
    """
    return (
        0.299 * rgb_array[:, :, 0] +
        0.587 * rgb_array[:, :, 1] +
        0.114 * rgb_array[:, :, 2]
    )


def compute_psnr(img1: Image.Image, img2: Image.Image) -> float:
    """Compute Peak Signal-to-Noise Ratio (PSNR) in dB between two images.

    Args:
        img1: Reference PIL Image.
        img2: Distorted PIL Image.

    Returns:
        float: PSNR value in dB (higher is better, >= 40 dB is near-lossless).
    """
    arr1 = np.array(img1.convert("RGB"), dtype=np.float32)
    arr2 = np.array(img2.convert("RGB"), dtype=np.float32)
    if arr1.shape != arr2.shape:
        return 0.0
    mse = float(np.mean((arr1 - arr2) ** 2))
    if mse <= 1e-12:
        return 100.0
    return float(20.0 * np.log10(255.0 / np.sqrt(mse)))


def embed_watermark(
    image: Image.Image,
    tile_mask: Optional[np.ndarray] = None,
    base: float = DEFAULT_BASE_STRENGTH,
    secret_key: str = DEFAULT_SECRET_KEY
) -> Image.Image:
    """Embed the DCT tile watermark into the luminance channel of an image.

    Args:
        image: PIL Image to watermark.
        tile_mask: Optional boolean 2D array of shape (H//64, W//64).
                   If None, marks all tiles (fully AI-generated).
        base: Base watermark embedding strength.
        secret_key: Secret key for watermark pattern derivation.

    Returns:
        Image.Image: Watermarked PIL Image (RGB).
    """
    img_rgb = image.convert("RGB")
    img_np = np.array(img_rgb, dtype=np.float32)
    H, W, _ = img_np.shape

    y = rgb_to_luminance(img_np)
    y_centered = y - 128.0
    delta_y = np.zeros((H, W), dtype=np.float32)

    pattern = get_watermark_pattern(secret_key)

    n_tiles_y = H // TILE_SIZE
    n_tiles_x = W // TILE_SIZE

    if tile_mask is None:
        tile_mask = np.ones((n_tiles_y, n_tiles_x), dtype=bool)

    for ty in range(n_tiles_y):
        for tx in range(n_tiles_x):
            if not tile_mask[ty, tx]:
                continue
            for by in range(8):
                for bx in range(8):
                    r0 = ty * TILE_SIZE + by * BLOCK_SIZE
                    c0 = tx * TILE_SIZE + bx * BLOCK_SIZE
                    block = y_centered[r0:r0 + BLOCK_SIZE, c0:c0 + BLOCK_SIZE]

                    # Texture masking: std / 15 clamped to [0.7, 2.0]
                    block_std = float(np.std(block))
                    alpha = base * float(np.clip(block_std / 15.0, 0.7, 2.0))

                    # 2D orthonormal DCT
                    dct_block = scipy.fft.dctn(block, norm="ortho")
                    for k in range(12):
                        dct_block[COEFF_ROWS[k], COEFF_COLS[k]] += alpha * pattern[k]

                    # Inverse DCT to compute pixel delta
                    new_block = scipy.fft.idctn(dct_block, norm="ortho")
                    delta_y[r0:r0 + BLOCK_SIZE, c0:c0 + BLOCK_SIZE] = new_block - block

    # Apply luminance delta directly to RGB channels
    marked_np = img_np + delta_y[:, :, None]
    marked_np = np.clip(np.round(marked_np), 0, 255).astype(np.uint8)
    return Image.fromarray(marked_np)


def detect_grid_vectorized(
    y_sub: np.ndarray,
    pattern: np.ndarray
) -> np.ndarray:
    """Vectorized calculation of tile z-scores across a luminance sub-image.

    Args:
        y_sub: 2D centered luminance sub-image array.
        pattern: Length-12 pattern vector.

    Returns:
        np.ndarray: 2D array of z-scores of shape (n_ty, n_tx).
    """
    H, W = y_sub.shape
    H_sub = (H // TILE_SIZE) * TILE_SIZE
    W_sub = (W // TILE_SIZE) * TILE_SIZE
    if H_sub == 0 or W_sub == 0:
        return np.zeros((0, 0), dtype=np.float32)

    cropped = y_sub[:H_sub, :W_sub]
    n_by = H_sub // BLOCK_SIZE
    n_bx = W_sub // BLOCK_SIZE

    # Shape: (n_by, n_bx, 8, 8)
    blocks = cropped.reshape(n_by, BLOCK_SIZE, n_bx, BLOCK_SIZE).transpose(0, 2, 1, 3)
    dct_blocks = scipy.fft.dctn(blocks, axes=(-2, -1), norm="ortho")

    # Extract 12 target coefficients: shape (n_by, n_bx, 12)
    coeffs = dct_blocks[:, :, COEFF_ROWS, COEFF_COLS]

    # Group 8x8 blocks into 64x64 tiles: shape (n_ty, n_tx, 64, 12)
    n_ty = H_sub // TILE_SIZE
    n_tx = W_sub // TILE_SIZE
    tile_coeffs = (
        coeffs.reshape(n_ty, 8, n_tx, 8, 12)
        .transpose(0, 2, 1, 3, 4)
        .reshape(n_ty, n_tx, 64, 12)
    )

    # z = Σ(c·p) / sqrt(Σc²)
    dot = np.sum(tile_coeffs * pattern, axis=(-2, -1))
    norm = np.sqrt(np.sum(tile_coeffs ** 2, axis=(-2, -1)) + 1e-12)
    return (dot / norm).astype(np.float32)


def detect_watermark(
    image: Image.Image,
    secret_key: str = DEFAULT_SECRET_KEY,
    sync_crop: bool = True
) -> Tuple[np.ndarray, Tuple[int, int], float, float]:
    """Detect DCT tile watermark, resynchronizing crop offsets if needed.

    Args:
        image: PIL Image to inspect.
        secret_key: Watermark secret key.
        sync_crop: If True, searches all 64 (dx, dy) grid offsets for crop resync.

    Returns:
        Tuple of:
            - z_matrix: 2D array of tile z-scores (shape n_ty, n_tx).
            - best_offset: (dy, dx) grid offset chosen.
            - fraction_marked: Fraction of tiles with z > 4.0.
            - global_z: Overall top-10% mean z-score.
    """
    img_rgb = image.convert("RGB")
    img_np = np.array(img_rgb, dtype=np.float32)
    y = rgb_to_luminance(img_np)
    y_centered = y - 128.0

    pattern = get_watermark_pattern(secret_key)

    # 1. Evaluate standard grid offset (0, 0) first
    z_mat_0 = detect_grid_vectorized(y_centered, pattern)
    if z_mat_0.size == 0:
        return z_mat_0, (0, 0), 0.0, 0.0

    top_k_0 = max(1, int(np.ceil(0.10 * len(z_mat_0.flatten()))))
    score_0 = float(np.mean(np.sort(z_mat_0.flatten())[-top_k_0:]))

    best_offset = (0, 0)
    best_score = score_0
    best_z_matrix = z_mat_0

    # 2. If offset (0, 0) is below detection threshold and sync_crop is requested,
    # evaluate remaining 63 offsets to resynchronize after an odd-pixel crop.
    if score_0 < DETECTION_THRESHOLD and sync_crop:
        for dy in range(BLOCK_SIZE):
            for dx in range(BLOCK_SIZE):
                if dy == 0 and dx == 0:
                    continue
                sub_y = y_centered[dy:, dx:]
                z_mat = detect_grid_vectorized(sub_y, pattern)
                if z_mat.size == 0:
                    continue

                top_k = max(1, int(np.ceil(0.10 * len(z_mat.flatten()))))
                score = float(np.mean(np.sort(z_mat.flatten())[-top_k:]))

                if score > best_score:
                    best_score = score
                    best_offset = (dy, dx)
                    best_z_matrix = z_mat

        # For an offset other than (0, 0) to be accepted as a valid crop resync,
        # it must clearly exceed the noise floor (clean images produce at most ~4.14 under 64 draws).
        if best_offset != (0, 0) and best_score < RESYNC_DETECTION_THRESHOLD:
            best_offset = (0, 0)
            best_score = score_0
            best_z_matrix = z_mat_0

    marked_tiles = best_z_matrix > DETECTION_THRESHOLD
    num_marked = int(np.sum(marked_tiles))
    fraction_marked = float(num_marked / best_z_matrix.size)

    if num_marked > 0:
        g_z = float(np.mean(best_z_matrix[marked_tiles]))
    else:
        g_z = float(best_score)

    return best_z_matrix, best_offset, fraction_marked, g_z


def generate_heatmap_overlay(
    image_size: Tuple[int, int],
    z_matrix: np.ndarray,
    offset: Tuple[int, int] = (0, 0),
    threshold: float = DETECTION_THRESHOLD
) -> Image.Image:
    """Generate a high-contrast RGBA heatmap overlay highlighting marked tiles.

    Args:
        image_size: (width, height) of original image.
        z_matrix: 2D array of tile z-scores.
        offset: (dy, dx) crop offset used during detection.
        threshold: z-score threshold for marking (default: 4.0).

    Returns:
        Image.Image: RGBA image overlay with red translucent tiles.
    """
    W, H = image_size
    overlay = np.zeros((H, W, 4), dtype=np.uint8)

    dy, dx = offset
    n_ty, n_tx = z_matrix.shape

    for ty in range(n_ty):
        for tx in range(n_tx):
            z = float(z_matrix[ty, tx])
            if z > threshold:
                # Scale opacity from 0.35 to 0.75 based on detection strength
                norm_z = min(1.0, max(0.0, (z - threshold) / 10.0))
                alpha = int(255 * (0.35 + 0.40 * norm_z))

                r0 = dy + ty * TILE_SIZE
                r1 = min(H, r0 + TILE_SIZE)
                c0 = dx + tx * TILE_SIZE
                c1 = min(W, c0 + TILE_SIZE)

                # Vibrant crimson red [255, 45, 85, alpha]
                overlay[r0:r1, c0:c1, 0] = 255
                overlay[r0:r1, c0:c1, 1] = 45
                overlay[r0:r1, c0:c1, 2] = 85
                overlay[r0:r1, c0:c1, 3] = alpha

                # Subtle darker border line around tile for crisp definition
                if r1 - r0 > 2 and c1 - c0 > 2:
                    overlay[r0, c0:c1, 3] = min(255, alpha + 50)
                    overlay[r1 - 1, c0:c1, 3] = min(255, alpha + 50)
                    overlay[r0:r1, c0, 3] = min(255, alpha + 50)
                    overlay[r0:r1, c1 - 1, 3] = min(255, alpha + 50)

    return Image.fromarray(overlay, mode="RGBA")
