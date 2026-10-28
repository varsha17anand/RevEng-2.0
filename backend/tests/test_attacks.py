"""Unit tests for attack implementations and labelers."""

import io
from PIL import Image
import numpy as np

from app.attacks import ATTACK_REGISTRY, apply_attack
from app.metadata import embed_metadata, IPTC_TRAINED_ALGORITHMIC
from app.labeler import instagram_mode_label, truthlens_label
from app.watermark import embed_watermark


def test_attacks_registry_presence():
    """Verify all 10 required attacks are implemented."""
    required = [
        "none", "screenshot_strip", "jpeg_q90", "jpeg_q75", "jpeg_q50",
        "crop_10_odd", "crop_jpeg_q75", "brightness_plus_10", "resize_0_9x", "resize_1_5x"
    ]
    for name in required:
        assert name in ATTACK_REGISTRY


def test_screenshot_attack_breaks_instagram_mode():
    """Verify screenshot attack strips metadata and breaks Instagram label."""
    img = Image.fromarray(np.full((128, 128, 3), 150, dtype=np.uint8))
    data = embed_metadata(img, IPTC_TRAINED_ALGORITHMIC, output_format="PNG")

    # Before attack: Instagram mode detects it
    res_before = instagram_mode_label(data)
    assert res_before["has_ai_label"] is True
    assert res_before["label"] == "AI info"

    # Screenshot attack
    attacked_img, attacked_bytes = apply_attack("screenshot_strip", img, data)

    # After attack: Instagram mode fails completely
    res_after = instagram_mode_label(attacked_bytes)
    assert res_after["has_ai_label"] is False
    assert res_after["label"] == "No AI info"


def test_truthlens_survives_screenshot_attack():
    """Verify TruthLens watermark survives screenshot attack."""
    img = Image.fromarray(np.full((512, 512, 3), 150, dtype=np.uint8))
    # Synthetic gradient so it has realistic frequency content
    arr = np.array(img, dtype=np.float32)
    for y in range(512):
        arr[y, :, :] += float(y % 30)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    wm = embed_watermark(img, base=3.5)
    data = embed_metadata(wm, IPTC_TRAINED_ALGORITHMIC, output_format="PNG")

    # Screenshot attack: strips metadata
    attacked_img, attacked_bytes = apply_attack("screenshot_strip", wm, data)

    # Instagram mode: FAILS
    ig_res = instagram_mode_label(attacked_bytes)
    assert ig_res["has_ai_label"] is False

    # TruthLens mode: SURVIVES
    tl_res = truthlens_label(attacked_img, attacked_bytes, sync_crop=True)
    assert tl_res["has_ai_label"] is True
    assert tl_res["fraction_marked"] > 0.0
