"""Comprehensive Testing & Validation Suite for TruthLens.

Mandatory verification items:
1. Clean sample images -> 0 tiles marked, label "No AI watermark" (all 6 samples)
2. Full Studio generate -> detected as AI-generated, provenance "verified"
3. Region edit (4 tiles) -> after screenshot_strip AND jpeg_q75 still labelled "AI-edited"
4. Instagram mode: metadata present -> "AI info"; after screenshot_strip -> "No AI info"
5. Edited manifest -> "tampered"; manifest signed with a different Ed25519 key -> "tampered"
6. C2PA/IPTC parser: synthetic JPEG/PNG/WebP with a C2PA box or IPTC tag -> detected; plain image -> not
7. Error handling: .txt upload -> 400; empty file -> 400; bad mode/attack/style -> 400;
   rectangle outside the image / zero-area -> 400; error messages contain no Python internals
8. Clean baseline through all 10 attacks -> 0 false-positive tiles
"""

import base64
import glob
import io
import json
import os
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from app.main import app, SAMPLE_METADATA, SAMPLES_DIR
from app.metadata import (
    embed_metadata,
    read_digital_source_type,
    has_c2pa_markers,
    IPTC_TRAINED_ALGORITHMIC,
    IPTC_COMPOSITE_ALGORITHMIC,
    PNG_CABX
)
from app.provenance import (
    create_manifest,
    verify_manifest,
    compute_pixel_hash
)
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

client = TestClient(app)


def test_clean_sample_images_zero_tiles():
    """All 6 clean sample images must yield 0 marked tiles and 'No AI watermark' label."""
    for meta in SAMPLE_METADATA:
        path = os.path.join(SAMPLES_DIR, meta["filename"])
        assert os.path.exists(path), f"Sample file {meta['filename']} missing from {SAMPLES_DIR}"
        with open(path, "rb") as f:
            data = f.read()

        res = client.post(
            "/api/analyze",
            files={"file": (meta["filename"], data, "image/jpeg")},
            data={"mode": "truthlens"}
        )
        assert res.status_code == 200, f"Analyze failed on {meta['filename']}: {res.text}"
        body = res.json()
        assert body["tiles_marked"] == 0, f"False positive tiles on clean image {meta['filename']}"
        assert body["fraction"] == 0.0
        assert body["has_ai_label"] is False
        assert body["label"] == "No AI watermark"


def test_full_studio_generate_verified():
    """Full studio generation must be detected as 'AI-generated' with 'verified' provenance."""
    res_gen = client.post(
        "/api/studio/generate",
        data={"prompt": "A vibrant university campus in autumn"}
    )
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["label"] == "AI-generated"
    assert "image_base64" in gen_data

    raw_b64 = gen_data["image_base64"]
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(raw_b64)

    # Analyze in TruthLens mode
    res_tl = client.post(
        "/api/analyze",
        files={"file": ("gen.png", img_bytes, "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_tl.status_code == 200
    body = res_tl.json()
    assert body["has_ai_label"] is True
    assert body["label"] == "AI-generated"
    assert body["provenance"] == "verified"
    assert body["tiles_marked"] > 0
    assert body["total_tiles"] == 64


def test_region_edit_survives_screenshot_and_jpeg75():
    """A 4-tile region edit must remain labelled 'AI-edited' after screenshot AND jpeg_q75 attacks."""
    # Create clean base image 512x512
    img = Image.fromarray(np.full((512, 512, 3), 130, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    base_bytes = buf.getvalue()

    # 4 tiles: (128, 128) to (256, 256) is exactly 2x2 = 4 tiles of 64x64
    res_edit = client.post(
        "/api/studio/edit",
        files={"file": ("base.png", base_bytes, "image/png")},
        data={"x1": 128, "y1": 128, "x2": 256, "y2": 256, "style": "cyberpunk"}
    )
    assert res_edit.status_code == 200
    edit_data = res_edit.json()
    assert edit_data["label"].startswith("AI-edited")

    raw_b64 = edit_data["image_base64"]
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    edited_bytes = base64.b64decode(raw_b64)

    # Attack A: screenshot_strip
    res_strip = client.post(
        "/api/attack",
        files={"file": ("edited.png", edited_bytes, "image/png")},
        data={"attack": "screenshot_strip"}
    )
    assert res_strip.status_code == 200
    strip_bytes = base64.b64decode(res_strip.json()["image_base64"].split(",", 1)[1])

    res_strip_tl = client.post(
        "/api/analyze",
        files={"file": ("strip.png", strip_bytes, "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_strip_tl.status_code == 200
    strip_body = res_strip_tl.json()
    assert strip_body["has_ai_label"] is True
    assert strip_body["label"].startswith("AI-edited"), f"Expected AI-edited, got {strip_body['label']}"
    assert strip_body["tiles_marked"] > 0

    # Attack B: jpeg_q75
    res_jpeg = client.post(
        "/api/attack",
        files={"file": ("edited.png", edited_bytes, "image/png")},
        data={"attack": "jpeg_q75"}
    )
    assert res_jpeg.status_code == 200
    jpeg_bytes = base64.b64decode(res_jpeg.json()["image_base64"].split(",", 1)[1])

    res_jpeg_tl = client.post(
        "/api/analyze",
        files={"file": ("jpeg.jpg", jpeg_bytes, "image/jpeg")},
        data={"mode": "truthlens"}
    )
    assert res_jpeg_tl.status_code == 200
    jpeg_body = res_jpeg_tl.json()
    assert jpeg_body["has_ai_label"] is True
    assert jpeg_body["label"].startswith("AI-edited"), f"Expected AI-edited, got {jpeg_body['label']}"
    assert jpeg_body["tiles_marked"] > 0


def test_instagram_mode_lifecycle():
    """Instagram mode detects metadata on generated image, but assigns 'No AI info' after screenshot attack."""
    res_gen = client.post(
        "/api/studio/generate",
        data={"prompt": "Autumn terrace"}
    )
    assert res_gen.status_code == 200
    img_bytes = base64.b64decode(res_gen.json()["image_base64"].split(",", 1)[1])

    # 1. Before attack: Instagram mode detects AI info and reports detection_signal
    res_ig = client.post(
        "/api/analyze",
        files={"file": ("gen.png", img_bytes, "image/png")},
        data={"mode": "instagram"}
    )
    assert res_ig.status_code == 200
    body = res_ig.json()
    assert body["has_ai_label"] is True
    assert body["label"] == "AI info"
    assert body["metadata_found"] is True
    assert "detection_signal" in body
    assert body["detection_signal"]["signal"] == "iptc"
    assert body["detection_signal"]["iptc_source_type"] == "trainedAlgorithmicMedia"
    assert body["detection_signal"]["c2pa"] is False

    # 2. Attack: screenshot_strip removes metadata
    res_strip = client.post(
        "/api/attack",
        files={"file": ("gen.png", img_bytes, "image/png")},
        data={"attack": "screenshot_strip"}
    )
    assert res_strip.status_code == 200
    stripped_bytes = base64.b64decode(res_strip.json()["image_base64"].split(",", 1)[1])

    # 3. After attack: Instagram mode completely misses it
    res_ig_stripped = client.post(
        "/api/analyze",
        files={"file": ("stripped.png", stripped_bytes, "image/png")},
        data={"mode": "instagram"}
    )
    assert res_ig_stripped.status_code == 200
    stripped_body = res_ig_stripped.json()
    assert stripped_body["has_ai_label"] is False
    assert stripped_body["label"] == "No AI info"
    assert stripped_body["metadata_found"] is False
    assert stripped_body["detection_signal"]["signal"] == "none"


def test_manifest_tampering_and_key_isolation():
    """Tampered manifest payload or manifest signed with foreign key must evaluate to 'tampered'."""
    img = Image.fromarray(np.full((128, 128, 3), 120, dtype=np.uint8))
    valid_manifest = create_manifest(image=img, action="generated", edited_tiles=None)

    # 1. Verify clean manifest passes
    status, reason = verify_manifest(img, valid_manifest)
    assert status == "verified"

    # 2. Tamper payload: change action to "tampered"
    tampered_manifest = json.loads(json.dumps(valid_manifest))
    tampered_manifest["payload"]["action"] = "malicious_tamper"
    status_t, reason_t = verify_manifest(img, tampered_manifest)
    assert status_t == "tampered"
    assert "signature verification failed" in reason_t.lower() or "invalid" in reason_t.lower()

    # 3. Tamper pixels: modify image pixels while keeping manifest signature
    tampered_img = Image.fromarray(np.full((128, 128, 3), 200, dtype=np.uint8))
    status_p, reason_p = verify_manifest(tampered_img, valid_manifest)
    assert status_p == "tampered"

    # 4. Attacker key replacement: sign payload with attacker's keypair
    attacker_priv = ed25519.Ed25519PrivateKey.generate()
    payload = valid_manifest["payload"]
    canonical_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    attacker_sig = attacker_priv.sign(canonical_bytes).hex()
    attacker_pub_hex = attacker_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ).hex()
    foreign_manifest = {
        "version": "1.0",
        "payload": payload,
        "signature": attacker_sig,
        "public_key": attacker_pub_hex
    }
    status_k, reason_k = verify_manifest(img, foreign_manifest)
    assert status_k == "tampered"
    assert "signature verification failed" in reason_k.lower()


def test_c2pa_iptc_parsers():
    """Test format-specific C2PA container detection and IPTC XMP parsing."""
    # 1. Synthetic PNG with caBX chunk
    img = Image.new("RGB", (32, 32), color="purple")
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add(PNG_CABX, b"test_c2pa_manifest_data")
    buf_cabx = io.BytesIO()
    img.save(buf_cabx, format="PNG", pnginfo=info)
    png_cabx_bytes = buf_cabx.getvalue()
    assert has_c2pa_markers(png_cabx_bytes) is True

    # Plain PNG
    buf_plain_png = io.BytesIO()
    img.save(buf_plain_png, format="PNG")
    assert has_c2pa_markers(buf_plain_png.getvalue()) is False

    # 2. Synthetic JPEG with APP11 (0xFFEB) JUMBF box carrying "c2pa"
    buf_jpeg = io.BytesIO()
    img.save(buf_jpeg, format="JPEG")
    raw_jpeg = buf_jpeg.getvalue()
    app11_payload = b"jumb\x00\x00\x00\x10jumdc2pa\x00\x00\x00\x00"
    app11_seg = b"\xff\xeb" + (len(app11_payload) + 2).to_bytes(2, "big") + app11_payload
    jpeg_with_c2pa = raw_jpeg[:2] + app11_seg + raw_jpeg[2:]
    assert has_c2pa_markers(jpeg_with_c2pa) is True

    # Plain JPEG
    assert has_c2pa_markers(raw_jpeg) is False

    # 3. Synthetic WebP with C2PA chunk
    header = b"RIFF" + (100).to_bytes(4, "little") + b"WEBP"
    c2pa_chunk = b"C2PA" + (10).to_bytes(4, "little") + b"1234567890"
    webp_with_c2pa = header + c2pa_chunk
    assert has_c2pa_markers(webp_with_c2pa) is True

    # Plain WebP
    plain_webp = header + b"VP8 " + (4).to_bytes(4, "little") + b"1234"
    assert has_c2pa_markers(plain_webp) is False

    # 4. IPTC trainedAlgorithmicMedia
    data_gen = embed_metadata(img, IPTC_TRAINED_ALGORITHMIC, output_format="PNG")
    assert read_digital_source_type(data_gen) == IPTC_TRAINED_ALGORITHMIC

    # 5. IPTC compositeWithTrainedAlgorithmicMedia
    data_edit = embed_metadata(img, IPTC_COMPOSITE_ALGORITHMIC, output_format="PNG")
    assert read_digital_source_type(data_edit) == IPTC_COMPOSITE_ALGORITHMIC

    # 6. Plain image bytes
    assert read_digital_source_type(buf_plain_png.getvalue()) is None


def test_error_handling_sanitized():
    """Verify error status codes (400) and sanitized error messages containing no internal Python internals."""
    img = Image.fromarray(np.full((256, 256, 3), 110, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    valid_bytes = buf.getvalue()

    # 1. Non-image .txt file upload -> 400
    res_txt = client.post(
        "/api/analyze",
        files={"file": ("notes.txt", b"Hello world! Not an image file.", "text/plain")},
        data={"mode": "truthlens"}
    )
    assert res_txt.status_code == 400
    detail = res_txt.json()["detail"]
    assert "unable to decode image data" in detail
    assert "_io." not in detail and "at 0x" not in detail

    # 2. Empty file upload -> 400
    res_empty = client.post(
        "/api/analyze",
        files={"file": ("empty.png", b"", "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # 3. Invalid mode -> 400
    res_mode = client.post(
        "/api/analyze",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"mode": "invalid_experimental_mode"}
    )
    assert res_mode.status_code == 400
    assert "invalid mode" in res_mode.json()["detail"].lower()

    # 4. Invalid attack -> 400
    res_attack = client.post(
        "/api/attack",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"attack": "invalid_quantum_attack"}
    )
    assert res_attack.status_code == 400
    assert "invalid attack" in res_attack.json()["detail"].lower()

    # 5. Invalid studio edit style -> 400
    res_style = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 50, "y1": 50, "x2": 150, "y2": 150, "style": "nonexistent_art_style"}
    )
    assert res_style.status_code == 400
    assert "unknown edit style" in res_style.json()["detail"].lower()

    # 6. Selection rectangle outside image dimensions -> 400
    res_oob = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 500, "y1": 500, "x2": 600, "y2": 600, "style": "cyberpunk"}
    )
    assert res_oob.status_code == 400
    assert "completely outside image dimensions" in res_oob.json()["detail"]

    # 7. Zero-area selection rectangle -> 400
    res_zero = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 100, "y1": 100, "x2": 100, "y2": 100, "style": "cyberpunk"}
    )
    assert res_zero.status_code == 400
    assert "invalid selection coordinates" in res_zero.json()["detail"].lower()

    # 8. Inverted selection rectangle -> 400
    res_inv = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 150, "y1": 150, "x2": 50, "y2": 50, "style": "cyberpunk"}
    )
    assert res_inv.status_code == 400
    assert "invalid selection coordinates" in res_inv.json()["detail"].lower()


def test_clean_baseline_attacks_zero_false_positives():
    """Clean baseline image through all 10 attacks must produce 0 false-positive tiles."""
    path = os.path.join(SAMPLES_DIR, "01_campus_quad.jpg")
    with open(path, "rb") as f:
        clean_bytes = f.read()

    res = client.post(
        "/api/attack-lab",
        files={"file": ("01_campus_quad.jpg", clean_bytes, "image/jpeg")}
    )
    assert res.status_code == 200
    rows = res.json()["rows"]
    assert len(rows) == 10

    for row in rows:
        assert row["tiles_marked"] == 0, (
            f"False positive on clean image under attack '{row['attack']}': {row['tiles_marked']} tiles marked"
        )
        assert row["truthlens_label"] == "No watermark"
