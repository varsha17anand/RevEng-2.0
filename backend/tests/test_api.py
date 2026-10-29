"""Integration tests for TruthLens FastAPI endpoints."""

import io
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_samples_endpoint():
    """Verify /api/samples lists sample images."""
    res = client.get("/api/samples")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "filename" in data[0]


def test_analyze_endpoint_clean():
    """Verify /api/analyze on a clean image."""
    img = Image.fromarray(np.full((128, 128, 3), 120, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Instagram mode
    res_ig = client.post(
        "/api/analyze",
        files={"file": ("test.png", buf.getvalue(), "image/png")},
        data={"mode": "instagram"}
    )
    assert res_ig.status_code == 200
    assert res_ig.json()["has_ai_label"] is False
    assert res_ig.json()["label"] == "No AI info"

    # TruthLens mode
    buf.seek(0)
    res_tl = client.post(
        "/api/analyze",
        files={"file": ("test.png", buf.getvalue(), "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_tl.status_code == 200
    assert res_tl.json()["has_ai_label"] is False
    assert res_tl.json()["label"] == "No AI watermark"


def test_studio_generate_and_analyze():
    """Verify studio generate followed by analysis in both modes."""
    res_gen = client.post(
        "/api/studio/generate",
        data={"prompt": "Autumn campus"}
    )
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert "image_base64" in gen_data
    assert gen_data["label"] == "AI-generated"

    # Extract base64 and send to analyze
    import base64
    raw_b64 = gen_data["image_base64"].split(",")[1]
    raw_bytes = base64.b64decode(raw_b64)

    # In Instagram mode: should show AI info (metadata embedded)
    res_ig = client.post(
        "/api/analyze",
        files={"file": ("gen.png", raw_bytes, "image/png")},
        data={"mode": "instagram"}
    )
    assert res_ig.status_code == 200
    assert res_ig.json()["has_ai_label"] is True
    assert res_ig.json()["label"] == "AI info"

    # In TruthLens mode: should show AI-generated with verified provenance
    res_tl = client.post(
        "/api/analyze",
        files={"file": ("gen.png", raw_bytes, "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_tl.status_code == 200
    assert res_tl.json()["has_ai_label"] is True
    assert res_tl.json()["provenance"] == "verified"


def test_attack_lab_endpoint():
    """Verify /api/attack-lab runs all attacks and returns comparison table."""
    img = Image.fromarray(np.full((128, 128, 3), 140, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = client.post(
        "/api/attack-lab",
        files={"file": ("test.png", buf.getvalue(), "image/png")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_attacks"] == 10
    assert len(data["rows"]) == 10
    # Check that screenshot_strip is in the rows
    screenshot_row = next((r for r in data["rows"] if r["attack"] == "screenshot_strip"), None)
    assert screenshot_row is not None
    assert screenshot_row["instagram_detected"] is False


def test_region_edit_survives_screenshot_attack():
    """Verify localized region edit retains graded 'AI-edited' label after screenshot strip."""
    import base64

    # 1. Base 512x512 image
    img = Image.fromarray(np.full((512, 512, 3), 130, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    base_bytes = buf.getvalue()

    # 2. Localized region edit (4 tiles: 128, 128, 256, 256)
    res_edit = client.post(
        "/api/studio/edit",
        files={"file": ("base.png", base_bytes, "image/png")},
        data={"x1": 128, "y1": 128, "x2": 256, "y2": 256, "style": "cyberpunk"}
    )
    assert res_edit.status_code == 200
    edit_data = res_edit.json()
    assert edit_data["label"].startswith("AI-edited")

    edit_bytes = base64.b64decode(edit_data["image_base64"].split(",")[1])

    # 3. Apply screenshot attack (metadata strip)
    res_attack = client.post(
        "/api/attack",
        files={"file": ("edited.png", edit_bytes, "image/png")},
        data={"attack": "screenshot_strip"}
    )
    assert res_attack.status_code == 200
    attacked_bytes = base64.b64decode(res_attack.json()["image_base64"].split(",")[1])

    # 4. Instagram mode must fail (metadata stripped)
    res_ig = client.post(
        "/api/analyze",
        files={"file": ("attacked.png", attacked_bytes, "image/png")},
        data={"mode": "instagram"}
    )
    assert res_ig.status_code == 200
    assert res_ig.json()["has_ai_label"] is False
    assert res_ig.json()["label"] == "No AI info"

    # 5. TruthLens mode MUST survive and retain graded 'AI-edited' label (NOT 'AI-generated' or 'No AI watermark')
    res_tl = client.post(
        "/api/analyze",
        files={"file": ("attacked.png", attacked_bytes, "image/png")},
        data={"mode": "truthlens"}
    )
    assert res_tl.status_code == 200
    assert res_tl.json()["has_ai_label"] is True
    assert res_tl.json()["label"].startswith("AI-edited")
    assert res_tl.json()["tiles_marked"] > 0


def test_input_validation_and_sanitized_errors():
    """Verify robust validation on invalid inputs and sanitized error messages."""
    img = Image.fromarray(np.full((256, 256, 3), 100, dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    valid_bytes = buf.getvalue()

    # 1. Unknown mode (e.g. 'banana') rejected with 400
    res_mode = client.post(
        "/api/analyze",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"mode": "banana"}
    )
    assert res_mode.status_code == 400
    assert "Invalid mode 'banana'" in res_mode.json()["detail"]

    # 2. Inverted box coordinates (x1 > x2) rejected with 400
    res_inv = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 200, "y1": 50, "x2": 50, "y2": 150, "style": "cyberpunk"}
    )
    assert res_inv.status_code == 400
    assert "Invalid selection coordinates" in res_inv.json()["detail"]

    # 3. Zero-size box coordinates (x1 == x2) rejected with 400
    res_zero = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 50, "y1": 50, "x2": 50, "y2": 100, "style": "cyberpunk"}
    )
    assert res_zero.status_code == 400
    assert "Invalid selection coordinates" in res_zero.json()["detail"]

    # 4. Box entirely outside image dimensions rejected with 400
    res_out = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 500, "y1": 500, "x2": 600, "y2": 600, "style": "cyberpunk"}
    )
    assert res_out.status_code == 400
    assert "completely outside image dimensions" in res_out.json()["detail"]

    # 5. Unknown style rejected with 400
    res_style = client.post(
        "/api/studio/edit",
        files={"file": ("test.png", valid_bytes, "image/png")},
        data={"x1": 50, "y1": 50, "x2": 150, "y2": 150, "style": "unknown_random_style"}
    )
    assert res_style.status_code == 400
    assert "Unknown edit style" in res_style.json()["detail"]

    # 6. Corrupted non-image file rejected without exposing internal Python memory addresses (_io.BytesIO at 0x...)
    corrupt_bytes = b"not_an_image_corrupt_data"
    res_corrupt = client.post(
        "/api/analyze",
        files={"file": ("broken.jpg", corrupt_bytes, "image/jpeg")},
        data={"mode": "truthlens"}
    )
    assert res_corrupt.status_code == 400
    detail = res_corrupt.json()["detail"]
    assert "unable to decode image data" in detail
    assert "BytesIO" not in detail
    assert "0x" not in detail


def test_non_square_image_generate_returns_512():
    """Non-square uploads to /api/studio/generate must return a 512×512 image (no distortion)."""
    import base64

    # Create a wide landscape image (800×400) — a simple solid-colour PNG
    wide_img = Image.fromarray(np.full((400, 800, 3), 120, dtype=np.uint8))
    buf = io.BytesIO()
    wide_img.save(buf, format="PNG")
    base_bytes = buf.getvalue()

    res = client.post(
        "/api/studio/generate",
        data={"prompt": "test landscape"},
        files={"file": ("wide.png", base_bytes, "image/png")},
    )
    assert res.status_code == 200, res.text

    raw_b64 = res.json()["image_base64"]
    # Strip optional data-URL prefix
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    result_bytes = base64.b64decode(raw_b64)
    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.size == (512, 512), (
        f"Expected 512×512 but got {result_img.size} — non-square upload was distorted"
    )


def test_non_square_image_edit_returns_512():
    """Non-square uploads to /api/studio/edit must return a 512×512 image (no distortion)."""
    import base64

    # Create a tall portrait image (300×600)
    tall_img = Image.fromarray(np.full((600, 300, 3), 80, dtype=np.uint8))
    buf = io.BytesIO()
    tall_img.save(buf, format="PNG")
    base_bytes = buf.getvalue()

    res = client.post(
        "/api/studio/edit",
        data={"x1": "100", "y1": "100", "x2": "300", "y2": "300", "style": "stylize"},
        files={"file": ("tall.png", base_bytes, "image/png")},
    )
    assert res.status_code == 200, res.text

    raw_b64 = res.json()["image_base64"]
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    result_bytes = base64.b64decode(raw_b64)
    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.size == (512, 512), (
        f"Expected 512×512 but got {result_img.size} — non-square upload was distorted"
    )
