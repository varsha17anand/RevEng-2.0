"""Pydantic schemas and response models for TruthLens API."""

from __future__ import annotations

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    """Detection analysis result for an uploaded image."""
    mode: str = Field(..., description="Analysis mode: 'instagram' or 'truthlens'")
    label: str = Field(..., description="Displayed badge label")
    has_ai_label: bool = Field(..., description="Whether an AI label is triggered")
    fraction: float = Field(0.0, description="Fraction of image tiles marked as AI (0.0 for metadata-only modes)")
    tiles_marked: int = Field(0, description="Count of positive AI tiles (0 for metadata-only modes)")
    total_tiles: int = Field(0, description="Total tiles analyzed (0 for metadata-only modes)")
    global_z: float = Field(0.0, description="Global top-10% mean z-score")
    heatmap_base64: Optional[str] = Field(None, description="Data URL of RGBA heatmap PNG")
    provenance: str = Field("none", description="'verified', 'tampered', or 'none'")
    provenance_details: str = Field("", description="Human-readable provenance info")
    metadata_found: bool = Field(False, description="Whether C2PA or IPTC metadata was present")
    timings_ms: float = Field(..., description="Server processing time in milliseconds")


class AttackLabRow(BaseModel):
    """Single row comparing Instagram vs TruthLens under a specific attack."""
    attack: str
    attack_name: str
    instagram_label: str
    instagram_detected: bool
    truthlens_label: str
    truthlens_detected: bool
    fraction_marked: float
    tiles_marked: int
    total_tiles: int
    global_z: float
    provenance_status: str


class AttackLabResponse(BaseModel):
    """Full Attack Lab comparison table."""
    rows: List[AttackLabRow]
    total_attacks: int
    timings_ms: float


class AttackResponse(BaseModel):
    """Result of applying an adversarial attack to an image."""
    attack: str
    image_base64: str
    format: str
    size: List[int]


class SampleItem(BaseModel):
    """Sample image item for testing."""
    id: str
    filename: str
    title: str
    url: str
    description: str


class StudioGenerateRequest(BaseModel):
    """Request payload for studio image generation."""
    prompt: Optional[str] = "A vibrant university campus in autumn"
    sample_id: Optional[str] = None


class StudioGenerateResponse(BaseModel):
    """Response from studio generation."""
    image_base64: str
    manifest: Dict[str, Any]
    label: str
    tiles_marked: int
    total_tiles: int


class StudioEditRequest(BaseModel):
    """Request payload for localized region editing."""
    x1: int
    y1: int
    x2: int
    y2: int
    style: Optional[str] = "cyberpunk"


class StudioEditResponse(BaseModel):
    """Response from studio region edit."""
    image_base64: str
    manifest: Dict[str, Any]
    label: str
    edited_tiles: List[List[int]]
    fraction_edited: float
