"""TruthLens Ed25519 Signed Provenance Manifest Engine.

Generates and cryptographically verifies signed provenance manifests.
If pixels or manifest contents are modified, status evaluates to 'tampered'.
If metadata is stripped, status evaluates to 'none'.

Security model
--------------
The server signs every image it produces with STUDIO_PRIVATE_KEY.
Verification always uses STUDIO_PUBLIC_KEY — the key that lives on this
server — never the public_key field embedded inside the manifest file.

This means:
  - An attacker who creates their own Ed25519 keypair, signs a fake claim,
    and embeds their public key in the manifest will receive status='tampered'
    (signature valid for their key but not for the server's pinned public key).
  - The public_key field in the manifest is stored only for auditability / UI
    display; it is never loaded as a trusted verification key.

Key loading priority
--------------------
1. TRUTHLENS_SIGNING_KEY environment variable — 32 raw bytes encoded as hex.
   Set this in Render → Environment → Secret Files / Env Vars.
   Example: TRUTHLENS_SIGNING_KEY=8c69cc5b11399916c736f70c7ebd9aefe882f132...
2. Fallback: deterministic demo key derived from a hardcoded seed.
   This fallback is only for local development; it is predictable and MUST NOT
   be relied upon for security — anyone who reads this source can derive it.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from PIL import Image
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key loading — server-side pinned keypair
# ---------------------------------------------------------------------------

def _load_signing_key() -> ed25519.Ed25519PrivateKey:
    """Load or derive the server's Ed25519 signing key.

    Checks TRUTHLENS_SIGNING_KEY env var (32 bytes as hex) first.
    Falls back to a deterministic demo seed with a warning.
    """
    env_val = os.environ.get("TRUTHLENS_SIGNING_KEY", "").strip()
    if env_val:
        try:
            raw = bytes.fromhex(env_val)
            if len(raw) != 32:
                raise ValueError(f"Expected 32 bytes, got {len(raw)}")
            key = ed25519.Ed25519PrivateKey.from_private_bytes(raw)
            logger.info("TruthLens: loaded Ed25519 signing key from TRUTHLENS_SIGNING_KEY env var")
            return key
        except Exception as exc:
            logger.error(
                "TruthLens: TRUTHLENS_SIGNING_KEY is set but invalid (%s). "
                "Falling back to demo key — set the env var correctly in Render.",
                exc
            )

    logger.warning(
        "TruthLens: TRUTHLENS_SIGNING_KEY not set. "
        "Using deterministic demo key (LOCAL DEV ONLY — not secure for production)."
    )
    demo_seed = hashlib.sha256(b"truthlens-studio-ed25519-demo-signing-key-2024").digest()
    return ed25519.Ed25519PrivateKey.from_private_bytes(demo_seed)


# Module-level singleton — loaded once at import time.
STUDIO_PRIVATE_KEY: ed25519.Ed25519PrivateKey = _load_signing_key()
STUDIO_PUBLIC_KEY: ed25519.Ed25519PublicKey = STUDIO_PRIVATE_KEY.public_key()
STUDIO_PUBLIC_KEY_HEX: str = STUDIO_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
).hex()


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

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
    private_key: ed25519.Ed25519PrivateKey = None,  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Create and cryptographically sign a TruthLens provenance manifest.

    Args:
        image: PIL Image being signed.
        action: \"generated\" or \"edited\".
        edited_tiles: Optional list of (row, col) tile indices edited.
        tool_name: Identifier for signing AI tool.
        private_key: Ed25519 private key. Defaults to STUDIO_PRIVATE_KEY.

    Returns:
        dict: Complete manifest with payload, Ed25519 signature, and
              the server's public key hex (for audit display only — the
              verifier will NOT use this value for trust decisions).
    """
    if private_key is None:
        private_key = STUDIO_PRIVATE_KEY

    pixel_hash = compute_pixel_hash(image)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payload = {
        "tool": tool_name,
        "action": action,
        "edited_tiles": [list(t) for t in (edited_tiles or [])],
        "image_sha256_of_pixels": pixel_hash,
        "timestamp": timestamp,
    }

    # Canonical JSON string for signature
    canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig_bytes = private_key.sign(canonical_bytes)

    # Store our own public key for auditability, not for trust
    return {
        "payload": payload,
        "signature": sig_bytes.hex(),
        "public_key": STUDIO_PUBLIC_KEY_HEX,  # always server key, informational only
    }


def verify_manifest(
    image: Image.Image,
    manifest: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    """Verify cryptographic authenticity and pixel integrity of a provenance manifest.

    Security guarantee: verification is always performed against the server's
    own pinned STUDIO_PUBLIC_KEY.  The public_key field inside the manifest is
    NEVER used for key loading, so substituting a different key in the file
    cannot produce a 'verified' result.

    Args:
        image: PIL Image to verify against manifest.
        manifest: Optional parsed manifest dictionary.

    Returns:
        Tuple of (status, reason):
            status: \"verified\" | \"tampered\" | \"none\"
            reason: Human-readable explanation.
    """
    if not manifest or "payload" not in manifest or "signature" not in manifest:
        return "none", "No signed provenance manifest present"

    payload = manifest["payload"]
    sig_hex = manifest.get("signature", "")

    # -----------------------------------------------------------------------
    # SECURITY: always verify against the server's pinned public key.
    # We deliberately do NOT read manifest["public_key"] for verification.
    # -----------------------------------------------------------------------
    try:
        sig_bytes = bytes.fromhex(sig_hex)
        canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        STUDIO_PUBLIC_KEY.verify(sig_bytes, canonical_bytes)
    except InvalidSignature:
        return (
            "tampered",
            "Ed25519 signature verification failed: invalid signature (manifest was not signed by this TruthLens server)"
        )
    except Exception as exc:
        return "tampered", f"Ed25519 signature verification failed: {exc}"

    # 2. Verify pixel hash matches current image pixels
    current_pixel_hash = compute_pixel_hash(image)
    recorded_hash = payload.get("image_sha256_of_pixels", "")

    if current_pixel_hash != recorded_hash:
        return (
            "tampered",
            "Pixel hash mismatch: image pixels were modified or cropped after signing",
        )

    tool = payload.get("tool", "TruthLens AI Studio")
    ts   = payload.get("timestamp", "")
    return "verified", f"Signed by {tool} · {ts}"
