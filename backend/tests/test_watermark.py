"""Unit tests for TruthLens DCT tile watermarking engine."""

import os
import glob
import numpy as np
import pytest
from PIL import Image

from app.watermark import (
    get_watermark_pattern,
    embed_watermark,
    detect_watermark,
    generate_heatmap_overlay,
    compute_psnr,
    DETECTION_THRESHOLD,
    TILE_SIZE
)


@pytest.fixture
def sample_image():
    """Load the first sample image or create a 512x512 synthetic photo."""
    samples = sorted(glob.glob("samples/*.jpg"))
    if samples:
        return Image.open(samples[0]).convert("RGB")
    # Synthetic fallback
    arr = np.zeros((512, 512, 3), dtype=np.uint8)
    for y in range(512):
        for x in range(512):
            arr[y, x] = [
                int(120 + 50 * np.sin(x / 30.0)),
                int(130 + 40 * np.cos(y / 40.0)),
                int(140 + 30 * np.sin((x + y) / 50.0))
            ]
    return Image.fromarray(arr)


def test_pattern_properties():
    """Test watermark pattern determinism, length, and value set."""
    p1 = get_watermark_pattern("key-alpha")
    p2 = get_watermark_pattern("key-alpha")
    p3 = get_watermark_pattern("key-beta")

    assert len(p1) == 12
    assert set(np.unique(p1)).issubset({-1.0, 1.0})
    assert np.array_equal(p1, p2)
    assert not np.array_equal(p1, p3)


def test_clean_image_no_false_positives(sample_image):
    """Verify that an unwatermarked image does not trigger tile detections."""
    z_matrix, offset, fraction_marked, global_z = detect_watermark(sample_image, sync_crop=False)
    
    assert z_matrix.size > 0
    # Clean images must have zero or near-zero false positive tiles
    num_marked = np.sum(z_matrix > DETECTION_THRESHOLD)
    assert num_marked == 0
    assert fraction_marked == 0.0
    assert abs(np.mean(z_matrix)) < 1.0


def test_watermark_imperceptibility_psnr(sample_image):
    """Verify that watermark embedding maintains PSNR >= 40 dB."""
    watermarked = embed_watermark(sample_image, base=3.5)
    psnr_val = compute_psnr(sample_image, watermarked)
    assert psnr_val >= 40.0, f"Expected PSNR >= 40 dB, got {psnr_val:.2f} dB"


def test_watermark_detection_full(sample_image):
    """Verify that fully watermarked images are detected with high confidence."""
    watermarked = embed_watermark(sample_image, base=3.5)
    z_matrix, offset, fraction_marked, global_z = detect_watermark(watermarked)

    assert fraction_marked > 0.35
    assert global_z > 4.0
    assert np.max(z_matrix) > 8.0


def test_partial_watermark_region(sample_image):
    """Verify localized tile watermarking for simulated AI edits."""
    W, H = sample_image.size
    n_ty, n_tx = H // TILE_SIZE, W // TILE_SIZE
    
    # Mark a 2x2 tile region at (0:2, 0:2)
    mask = np.zeros((n_ty, n_tx), dtype=bool)
    mask[0:2, 0:2] = True
    
    partially_marked = embed_watermark(sample_image, tile_mask=mask, base=3.5)
    z_matrix, offset, fraction_marked, global_z = detect_watermark(partially_marked, sync_crop=False)
    
    # Check that marked region tiles are detected
    detected_mask = z_matrix > DETECTION_THRESHOLD
    for r in range(0, 2):
        for c in range(0, 2):
            assert z_matrix[r, c] > DETECTION_THRESHOLD

    # Outside regions should remain largely unmarked
    outside_mask = np.copy(detected_mask)
    outside_mask[0:2, 0:2] = False
    assert np.sum(outside_mask) == 0


def test_crop_resynchronization(sample_image):
    """Verify detector can resync after odd-pixel cropping."""
    watermarked = embed_watermark(sample_image, base=4.2)
    
    # Crop with odd offsets: dy=19, dx=13
    W, H = watermarked.size
    cropped = watermarked.crop((13, 19, W - 20, H - 20))
    
    z_matrix, best_offset, fraction_marked, global_z = detect_watermark(cropped, sync_crop=True)
    
    # Expected offset to re-align with 8x8 DCT grid:
    # 19 % 8 = 3 -> offset needed is (8 - 3) = 5
    # 13 % 8 = 5 -> offset needed is (8 - 5) = 3
    expected_dy = (8 - (19 % 8)) % 8
    expected_dx = (8 - (13 % 8)) % 8
    
    assert best_offset == (expected_dy, expected_dx)
    assert fraction_marked > 0.40
    assert global_z > 4.0


def test_heatmap_generation(sample_image):
    """Verify heatmap overlay dimensions, RGBA mode, and alpha values."""
    watermarked = embed_watermark(sample_image, base=4.2)
    z_matrix, offset, fraction_marked, global_z = detect_watermark(watermarked)
    
    overlay = generate_heatmap_overlay(sample_image.size, z_matrix, offset=offset)
    assert overlay.size == sample_image.size
    assert overlay.mode == "RGBA"
    
    arr = np.array(overlay)
    # Check that some pixels have non-zero alpha
    assert np.any(arr[:, :, 3] > 0)
