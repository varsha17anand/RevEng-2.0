"""TruthLens FastAPI Application.

Serves the TruthLens REST API for:
- Simulated AI Studio (generation and localized tile-based editing)
- Dual-mode image analysis (Instagram mode vs TruthLens mode)
- Adversarial Attack Lab suite
- Sample image browser
- Static frontend production serving
"""

from __future__ import annotations

import base64
import io
import os
import time
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from app.watermark import (
    generate_heatmap_overlay,
    DETECTION_THRESHOLD,
    TILE_SIZE
)
from app.labeler import instagram_mode_label, truthlens_label
from app.attacks import ATTACK_REGISTRY, apply_attack
from app.ai_edit import generate_ai_image, edit_ai_region
from app.schemas import (
    AnalyzeResponse,
    AttackLabResponse,
    AttackLabRow,
    AttackResponse,
    SampleItem,
    StudioGenerateResponse,
    StudioEditResponse
)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI(
    title="TruthLens API",
    description="Reverse-engineered Instagram AI-info pipeline with graded DCT tile watermarks and Ed25519 provenance.",
    version="1.0.0"
)

# Enable CORS for local dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_METADATA = [
    {
        "id": "campus_quad",
        "filename": "01_campus_quad.jpg",
        "title": "University Campus Quad",
        "description": "Historic university library, autumn trees, and brick walking path in bright daylight."
    },
    {
        "id": "portrait_student",
        "filename": "02_portrait_student.jpg",
        "title": "Student Portrait",
        "description": "Natural daylight portrait of a college student holding a notebook on an outdoor terrace."
    },
    {
        "id": "city_skyline",
        "filename": "03_city_skyline.jpg",
        "title": "Metropolitan City Skyline",
        "description": "Vibrant city skyline with glass architecture and reflection over water."
    },
    {
        "id": "coffee_scene",
        "filename": "04_coffee_scene.jpg",
        "title": "Cafe Still Life",
        "description": "Artisan coffee cup with latte art on a rustic wooden table with open journal."
    },
    {
        "id": "nature_lake",
        "filename": "05_nature_lake.jpg",
        "title": "Alpine Mountain Lake",
        "description": "Turquoise glacial mountain lake surrounded by pine forests and snowy peaks."
    },
    {
        "id": "architecture_hall",
        "filename": "06_architecture_hall.jpg",
        "title": "Campus Architecture",
        "description": "Architectural study of brick tower facades and arched windows."
    }
]


def validate_image_file(file: UploadFile, content: bytes) -> Image.Image:
    """Validate uploaded file size, content-type, and decodability."""
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE // (1024*1024)} MB")
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        # Re-open after verify() because verify() exhausts image state
        return Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")


def image_to_base64_data_url(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL image to data URL string."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def bytes_to_base64_data_url(data: bytes, format: str = "PNG") -> str:
    """Convert raw image bytes to data URL string."""
    encoded = base64.b64encode(data).decode("utf-8")
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
if not os.path.exists(SAMPLES_DIR):
    SAMPLES_DIR = os.path.abspath("samples")


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TruthLens"}


@app.get("/api/samples", response_model=List[SampleItem])
def list_samples():
    """Return available pre-loaded sample images for testing."""
    items = []
    for meta in SAMPLE_METADATA:
        full_path = os.path.join(SAMPLES_DIR, meta["filename"])
        if os.path.exists(full_path):
            items.append(SampleItem(
                id=meta["id"],
                filename=meta["filename"],
                title=meta["title"],
                url=f"/api/samples/{meta['filename']}",
                description=meta["description"]
            ))
    return items


@app.get("/api/samples/{filename}")
def get_sample_image(filename: str):
    """Serve a sample image file."""
    # Sanitize filename
    safe_name = os.path.basename(filename)
    path = os.path.join(SAMPLES_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Sample image not found")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_image(
    file: UploadFile = File(...),
    mode: str = Form("truthlens")
):
    """Analyze an image using Instagram mode or TruthLens mode."""
    t0 = time.time()
    content = file.file.read()
    img = validate_image_file(file, content)

    mode_lower = mode.strip().lower()

    if mode_lower == "instagram":
        res = instagram_mode_label(content)
        t1 = time.time()
        return AnalyzeResponse(
            mode="instagram",
            label=res["label"],
            has_ai_label=res["has_ai_label"],
            fraction=1.0 if res["has_ai_label"] else 0.0,
            tiles_marked=64 if res["has_ai_label"] else 0,
            total_tiles=64,
            global_z=0.0,
            heatmap_base64=None,
            provenance="none",
            provenance_details="Instagram evaluates only C2PA/IPTC metadata; pixel watermark is ignored.",
            metadata_found=res["metadata_found"],
            timings_ms=round((t1 - t0) * 1000, 2)
        )
    else:
        # TruthLens mode
        res = truthlens_label(img, content, sync_crop=True)
        z_matrix = res["z_matrix"]
        offset = res["crop_offset"]

        # Generate heatmap PNG overlay if any tiles detected
        heatmap_url = None
        if res["tiles_marked"] > 0 and z_matrix.size > 0:
            overlay = generate_heatmap_overlay(img.size, z_matrix, offset=offset)
            heatmap_url = image_to_base64_data_url(overlay, format="PNG")

        t1 = time.time()
        return AnalyzeResponse(
            mode="truthlens",
            label=res["label"],
            has_ai_label=res["has_ai_label"],
            fraction=res["display_fraction"],   # labelled percentage, not raw watermark fraction
            tiles_marked=res["tiles_marked"],
            total_tiles=res["total_tiles"],
            global_z=res["global_z"],
            heatmap_base64=heatmap_url,
            provenance=res["provenance_status"],
            provenance_details=res["provenance_details"],
            metadata_found=res["metadata_present"],
            timings_ms=round((t1 - t0) * 1000, 2)
        )


@app.post("/api/attack", response_model=AttackResponse)
def run_single_attack(
    file: UploadFile = File(...),
    attack: str = Form(...)
):
    """Apply an adversarial attack to an image and return modified image data."""
    content = file.file.read()
    img = validate_image_file(file, content)

    if attack not in ATTACK_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Invalid attack: {attack}. Choose from {list(ATTACK_REGISTRY.keys())}")

    attacked_img, attacked_bytes = apply_attack(attack, img, content)
    fmt = "JPEG" if "jpeg" in attack else "PNG"
    b64 = bytes_to_base64_data_url(attacked_bytes, format=fmt)

    return AttackResponse(
        attack=attack,
        image_base64=b64,
        format=fmt,
        size=[attacked_img.width, attacked_img.height]
    )


@app.post("/api/attack-lab", response_model=AttackLabResponse)
def run_attack_lab(
    file: UploadFile = File(...)
):
    """Run all 10 attacks on the uploaded image and return comparative results."""
    t0 = time.time()
    content = file.file.read()
    img = validate_image_file(file, content)

    rows: List[AttackLabRow] = []

    attack_labels = {
        "none": "Baseline (No Attack)",
        "screenshot_strip": "Screenshot / Metadata Strip",
        "jpeg_q90": "JPEG Quality 90",
        "jpeg_q75": "JPEG Quality 75",
        "jpeg_q50": "JPEG Quality 50 (Aggressive)",
        "crop_10_odd": "Crop 10% (Odd Pixel Offset)",
        "crop_jpeg_q75": "Crop 10% + JPEG q75",
        "brightness_plus_10": "Brightness +10%",
        "resize_0_9x": "Resize Down 0.9x",
        "resize_1_5x": "Resize Up 1.5x"
    }

    for att_key in ATTACK_REGISTRY.keys():
        att_img, att_bytes = apply_attack(att_key, img, content)

        # Instagram analysis (evaluates file metadata)
        ig_res = instagram_mode_label(att_bytes)

        # TruthLens analysis
        tl_res = truthlens_label(att_img, att_bytes, sync_crop=True)

        # In the Attack Lab, evaluate the survival of the pixel DCT watermark itself
        # so that defeated attacks (e.g. continuous resizing) show DEFEATED / No watermark.
        watermark_survived = tl_res["tiles_marked"] > 0
        tl_display_label = tl_res["label"] if watermark_survived else "No watermark"

        rows.append(AttackLabRow(
            attack=att_key,
            attack_name=attack_labels.get(att_key, att_key),
            instagram_label=ig_res["label"],
            instagram_detected=ig_res["has_ai_label"],
            truthlens_label=tl_display_label,
            truthlens_detected=watermark_survived,
            fraction_marked=tl_res["fraction_marked"],
            tiles_marked=tl_res["tiles_marked"],
            total_tiles=tl_res["total_tiles"],
            global_z=round(tl_res["global_z"], 2),
            provenance_status=tl_res["provenance_status"]
        ))

    t1 = time.time()
    return AttackLabResponse(
        rows=rows,
        total_attacks=len(rows),
        timings_ms=round((t1 - t0) * 1000, 2)
    )


@app.post("/api/studio/generate", response_model=StudioGenerateResponse)
def studio_generate(
    file: Optional[UploadFile] = File(None),
    prompt: str = Form("A scenic university campus at sunset"),
    sample_id: Optional[str] = Form(None)
):
    """Generate a simulated AI image, fully marked with signed provenance."""
    base_img = None
    if file:
        content = file.file.read()
        base_img = validate_image_file(file, content)
    elif sample_id:
        match = next((s for s in SAMPLE_METADATA if s["id"] == sample_id), None)
        if match:
            path = os.path.join(SAMPLES_DIR, match["filename"])
            if os.path.exists(path):
                base_img = Image.open(path).convert("RGB")

    seed = (abs(hash(prompt)) % 10000) if prompt else 42
    watermarked_img, img_bytes, manifest = generate_ai_image(prompt=prompt, seed=seed, base_image=base_img)
    b64 = bytes_to_base64_data_url(img_bytes, format="PNG")

    n_ty = watermarked_img.height // TILE_SIZE
    n_tx = watermarked_img.width // TILE_SIZE
    total_tiles = n_ty * n_tx

    return StudioGenerateResponse(
        image_base64=b64,
        manifest=manifest,
        label="AI-generated",
        tiles_marked=total_tiles,
        total_tiles=total_tiles
    )


@app.post("/api/studio/edit", response_model=StudioEditResponse)
def studio_edit(
    file: UploadFile = File(...),
    x1: int = Form(...),
    y1: int = Form(...),
    x2: int = Form(...),
    y2: int = Form(...),
    style: str = Form("cyberpunk")
):
    """Apply localized AI edit inside a rectangle, marking only those tiles."""
    content = file.file.read()
    img = validate_image_file(file, content)

    box = (x1, y1, x2, y2)
    edited_img, img_bytes, manifest, edited_tiles = edit_ai_region(img, box, edit_style=style)
    b64 = bytes_to_base64_data_url(img_bytes, format="PNG")

    n_ty = edited_img.height // TILE_SIZE
    n_tx = edited_img.width // TILE_SIZE
    total_tiles = max(1, n_ty * n_tx)
    frac = len(edited_tiles) / total_tiles
    pct = max(1, round(frac * 100))

    return StudioEditResponse(
        image_base64=b64,
        manifest=manifest,
        label=f"AI-edited: {pct}% of image",
        edited_tiles=[list(t) for t in edited_tiles],
        fraction_edited=frac
    )


# Serve built frontend static files if distribution directory exists
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        app.mount("/static", StaticFiles(directory=assets_dir), name="static")

    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
