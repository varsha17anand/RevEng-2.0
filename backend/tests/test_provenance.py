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


def test_provenance_rejects_attacker_key():
    """Verify that an attacker signing false claims with their own key is rejected as tampered."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    import json
    import secrets

    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))

    # Attacker generates their own fresh keypair
    attacker_priv = ed25519.Ed25519PrivateKey.generate()
    attacker_pub = attacker_priv.public_key()
    attacker_pub_hex = attacker_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ).hex()

    # Attacker crafts false claim
    pixel_hash = compute_pixel_hash(img)
    payload = {
        "tool": "Canon EOS R5 real camera photo",
        "action": "camera_capture",
        "edited_tiles": [],
        "image_sha256_of_pixels": pixel_hash,
        "timestamp": "2024-01-01T00:00:00Z"
    }

    canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    attacker_sig = attacker_priv.sign(canonical_bytes).hex()

    fake_manifest = {
        "payload": payload,
        "signature": attacker_sig,
        "public_key": attacker_pub_hex
    }

    # Must be rejected because TruthLens verifier strictly checks against server's pinned key
    status, reason = verify_manifest(img, fake_manifest)
    assert status == "tampered"
    assert "signature verification failed" in reason


def test_provenance_env_var_key(monkeypatch):
    """Verify that TRUTHLENS_SIGNING_KEY env var loads and signs/verifies correctly."""
    import secrets
    from app import provenance

    # Generate 32 bytes hex key
    test_key_bytes = secrets.token_bytes(32)
    test_key_hex = test_key_bytes.hex()
    monkeypatch.setenv("TRUTHLENS_SIGNING_KEY", test_key_hex)

    loaded_key = provenance._load_signing_key()
    assert loaded_key is not None

    img = Image.fromarray(np.full((128, 128, 3), 100, dtype=np.uint8))
    # Test signing with loaded key
    manifest = provenance.create_manifest(img, action="generated", private_key=loaded_key)
    # If server has loaded_key as its key
    monkeypatch.setattr(provenance, "STUDIO_PUBLIC_KEY", loaded_key.public_key())
    status, reason = provenance.verify_manifest(img, manifest)
    assert status == "verified"
