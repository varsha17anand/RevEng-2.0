"""Unit tests for Ed25519 signed provenance manifests."""

from PIL import Image
import numpy as np

from app.provenance import (
    create_manifest,
    verify_manifest,
    compute_pixel_hash,
    STUDIO_PRIVATE_KEY
)


def test_provenance_create_and_verify():
    """Verify valid signed manifest creation and verification."""
    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))
    manifest = create_manifest(img, action="generated")

    status, reason = verify_manifest(img, manifest)
    assert status == "verified"
    assert "TruthLens AI Studio" in reason


def test_provenance_tampered_pixels():
    """Verify that tampering with image pixels flags manifest as tampered."""
    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))
    manifest = create_manifest(img, action="generated")

    # Modify a pixel
    tampered_img = Image.fromarray(np.full((128, 128, 3), 101, dtype=np.uint8))
    status, reason = verify_manifest(tampered_img, manifest)

    assert status == "tampered"
    assert "Pixel hash mismatch" in reason


def test_provenance_tampered_signature():
    """Verify that forged signature or payload tampering is flagged as tampered."""
    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))
    manifest = create_manifest(img, action="generated")

    # Forged action
    manifest["payload"]["action"] = "tampered_action"
    status, reason = verify_manifest(img, manifest)

    assert status == "tampered"
    assert "signature verification failed" in reason


def test_provenance_missing():
    """Verify that missing manifest returns 'none'."""
    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))
    status, reason = verify_manifest(img, None)

    assert status == "none"
