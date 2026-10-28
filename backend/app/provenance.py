"""TruthLens Ed25519 Signed Provenance Manifest Engine.

Generates and cryptographically verifies signed provenance manifests.
If pixels or manifest contents are modified, status evaluates to 'tampered'.
If metadata is stripped, status evaluates to 'none'.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from PIL import Image
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Standard demo signing key for TruthLens Studio
_DEMO_SEED = hashlib.sha256(b"truthlens-studio-ed25519-demo-signing-key-2024").digest()
STUDIO_PRIVATE_KEY = ed25519.Ed25519PrivateKey.from_private_bytes(_DEMO_SEED)
STUDIO_PUBLIC_KEY = STUDIO_PRIVATE_KEY.public_key()
STUDIO_PUBLIC_KEY_HEX = STUDIO_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
).hex()


def compute_pixel_hash(image: Image.Image) -> str:
    """Compute deterministic SHA-256 hash of RGB pixel data.

    Args:
        image: PIL Image.

    Returns:
        str: Hex SHA-256 digest of pure RGB byte buffer.
    """
    img_rgb = image.convert("RGB")
    pixel_bytes = np.ascontiguousarray(np.array(img_rgb, dtype=np.uint8)).tobytes()
    return hashlib.sha256(pixel_bytes).hexdigest()


def create_manifest(
    image: Image.Image,
    action: str = "generated",
    edited_tiles: Optional[List[Tuple[int, int]]] = None,
    tool_name: str = "TruthLens AI Studio v1.0",
    private_key: ed25519.Ed25519PrivateKey = STUDIO_PRIVATE_KEY
) -> Dict[str, Any]:
    """Create and cryptographically sign a TruthLens provenance manifest.

    Args:
        image: PIL Image being signed.
        action: "generated" or "edited".
        edited_tiles: Optional list of (row, col) tile indices edited.
        tool_name: Identifier for signing AI tool.
        private_key: Ed25519 private key.

    Returns:
        dict: Complete manifest with payload, Ed25519 signature, and public key.
    """
    pixel_hash = compute_pixel_hash(image)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payload = {
        "tool": tool_name,
        "action": action,
        "edited_tiles": [list(t) for t in (edited_tiles or [])],
        "image_sha256_of_pixels": pixel_hash,
        "timestamp": timestamp
    }

    # Canonical JSON string for signature
    canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig_bytes = private_key.sign(canonical_bytes)

    pubkey_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return {
        "payload": payload,
        "signature": sig_bytes.hex(),
        "public_key": pubkey_bytes.hex()
    }


def verify_manifest(
    image: Image.Image,
    manifest: Optional[Dict[str, Any]]
) -> Tuple[str, str]:
    """Verify cryptographic authenticity and pixel integrity of provenance manifest.

    Args:
        image: PIL Image to verify against manifest.
        manifest: Optional parsed manifest dictionary.

    Returns:
        Tuple of (status, reason):
            status: "verified" | "tampered" | "none"
            reason: Human-readable explanation.
    """
    if not manifest or "payload" not in manifest or "signature" not in manifest:
        return "none", "No signed provenance manifest present"

    payload = manifest["payload"]
    sig_hex = manifest.get("signature", "")
    pubkey_hex = manifest.get("public_key", STUDIO_PUBLIC_KEY_HEX)

    try:
        sig_bytes = bytes.fromhex(sig_hex)
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pubkey_bytes)

        # 1. Verify Ed25519 digital signature
        canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        public_key.verify(sig_bytes, canonical_bytes)
    except (InvalidSignature, ValueError, Exception) as e:
        return "tampered", f"Ed25519 signature verification failed: invalid signature ({str(e)})"

    # 2. Verify pixel hash matches current image pixels
    current_pixel_hash = compute_pixel_hash(image)
    recorded_hash = payload.get("image_sha256_of_pixels", "")

    if current_pixel_hash != recorded_hash:
        return "tampered", "Pixel hash mismatch: image pixels were modified or cropped after signing"

    return "verified", f"Signed by {payload.get('tool', 'Verified AI Tool')} on {payload.get('timestamp', '')}"
