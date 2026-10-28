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
