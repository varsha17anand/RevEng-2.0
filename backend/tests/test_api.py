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
