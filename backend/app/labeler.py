"""TruthLens and Instagram-Mode Decision Labelers.

Implements Instagram mode (pure metadata & C2PA check) alongside
TruthLens mode (graded DCT tile watermark + signed Ed25519 provenance).
"""

from __future__ import annotations

import json
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image

from app.watermark import detect_watermark, DETECTION_THRESHOLD, GENERATED_THRESHOLD, TILE_SIZE
from app.metadata import read_digital_source_type, has_c2pa_markers, extract_provenance_raw
from app.provenance import verify_manifest


def instagram_mode_label(image_bytes: bytes) -> Dict[str, Any]:
    """Evaluate image using Meta/Instagram's closed-source AI info heuristic.

    Instagram checks if IPTC DigitalSourceType is present in XMP or if C2PA manifest
    markers (JPEG APP11 JUMBF, PNG caBX, WebP C2PA) are in the file container.
    If metadata is stripped, no label is assigned.

    Args:
        image_bytes: Raw image file bytes.

    Returns:
        dict: Label result conforming to Instagram behavior.
    """
    digital_source = read_digital_source_type(image_bytes)
    has_c2pa = has_c2pa_markers(image_bytes)

    detected = (digital_source is not None) or has_c2pa

    iptc_short = digital_source.split("/")[-1] if digital_source else None

    if has_c2pa:
        signal = "c2pa"
    elif digital_source:
        signal = "iptc"
    else:
        signal = "none"

    if detected:
        reason_parts = []
        if digital_source:
            if iptc_short == "compositeWithTrainedAlgorithmicMedia":
                reason_parts.append("IPTC DigitalSourceType (compositeWithTrainedAlgorithmicMedia - AI-edited)")
            else:
                reason_parts.append(f"IPTC DigitalSourceType ({iptc_short})")
        if has_c2pa:
            reason_parts.append("C2PA manifest container markers")
        reason = "Detected via " + " and ".join(reason_parts)
        label = "AI info"
    else:
        label = "No AI info"
        reason = "No C2PA manifest or IPTC DigitalSourceType found in file metadata"

    detection_signal = {
        "c2pa": bool(has_c2pa),
        "iptc_source_type": iptc_short,
        "signal": signal,
    }

    return {
        "mode": "instagram",
        "label": label,
        "has_ai_label": detected,
        "reason": reason,
        "metadata_found": detected,
        "digital_source_type": digital_source,
        "has_c2pa": has_c2pa,
        "c2pa": bool(has_c2pa),
        "iptc_source_type": iptc_short,
        "signal": signal,
        "detection_signal": detection_signal
    }


def truthlens_label(
    image: Image.Image,
    image_bytes: bytes,
    sync_crop: bool = True
) -> Dict[str, Any]:
    """Evaluate image using TruthLens multi-layered pixel & provenance engine.

    1. Scans pixel luminance in orthonormal DCT domain for 64x64 tile watermarks.
    2. Resynchronizes grid offsets to survive crops and resizes.
    3. Produces a graded label: 'AI-generated' | 'AI-edited: N% of image' | 'No AI watermark'.
    4. Evaluates Ed25519 signed provenance manifest: 'verified' | 'tampered' | 'none'.

    Args:
        image: PIL Image object.
        image_bytes: Raw file bytes for provenance extraction.
        sync_crop: Enable 64-offset grid resync.

    Returns:
        dict: Comprehensive analysis result.
    """
    # 1. DCT Tile Watermark Detection
    z_matrix, offset, fraction_marked, global_z = detect_watermark(image, sync_crop=sync_crop)

    total_tiles = z_matrix.size
    tiles_marked = int(np_sum := (z_matrix > DETECTION_THRESHOLD).sum())

    # 2. Signed Provenance Verification
    raw_manifest_str = extract_provenance_raw(image_bytes)
    manifest_obj = None
    if raw_manifest_str:
        try:
            manifest_obj = json.loads(raw_manifest_str)
        except Exception:
            pass

    prov_status, prov_reason = verify_manifest(image, manifest_obj)

    # Check if standard metadata exists
    digital_source = read_digital_source_type(image_bytes)
    has_c2pa = has_c2pa_markers(image_bytes)
    metadata_present = (digital_source is not None) or has_c2pa

    manifest_action = None
    if manifest_obj and isinstance(manifest_obj, dict):
        manifest_action = manifest_obj.get("payload", {}).get("action")

    marked_mask = z_matrix > DETECTION_THRESHOLD
    tiles_marked = int(np_sum := marked_mask.sum())
    has_watermark = tiles_marked > 0

    bbox_coverage = 0.0
    if tiles_marked > 0:
        rows, cols = np.where(marked_mask)
        r_span = int(np.max(rows) - np.min(rows) + 1)
        c_span = int(np.max(cols) - np.min(cols) + 1)
        bbox_coverage = (r_span * c_span) / float(total_tiles)

    # 3. Graded label decision:
    # Uses verified manifest/IPTC metadata when available, or relies on robust DCT watermark
    # spatial distribution when metadata is stripped (e.g. screenshot attack).
    #
    # display_fraction: the percentage shown to the user in the label (0.0–1.0).
    #   - "AI-generated":           tiles_marked / total_tiles  (actual detected tiles)
    #   - "AI-edited: N% of image": tiles from manifest edited_tiles list / total_tiles
    #                               OR tiles_marked / total_tiles when metadata is gone
    #   - "No AI watermark":        0.0
    display_fraction: float = 0.0

    if manifest_action == "generated" or (digital_source and "trainedAlgorithmicMedia" in digital_source):
        label = "AI-generated"
        has_ai_label = True
        # For display use actual detected tile fraction (may be < 1.0 after screenshot JPEG loss)
        display_fraction = float(tiles_marked) / float(total_tiles)
    elif manifest_action == "edited" or (digital_source and "compositeWithTrainedAlgorithmicMedia" in digital_source):
        edited_list = manifest_obj.get("payload", {}).get("edited_tiles", []) if manifest_obj else []
        if edited_list:
            # Use the authoritative edited tile count from the signed manifest
            pct = max(1, round((len(edited_list) / float(total_tiles)) * 100))
            display_fraction = len(edited_list) / float(total_tiles)
        else:
            # Metadata action present but no tile list — fall back to detected tile count
            pct = max(1, round(fraction_marked * 100))
            display_fraction = fraction_marked
        label = f"AI-edited: {pct}% of image"
        has_ai_label = True
    elif has_watermark:
        # Watermark detected without metadata (e.g. screenshot attack / metadata strip):
        # A fully generated image has watermarked tiles spanning across the entire image (bbox_coverage >= 70%),
        # a high overall tile mean, and widespread tile detections.
        mean_all = float(np.mean(z_matrix))
        is_full_gen = (
            (bbox_coverage >= 0.70 and fraction_marked >= 0.28 and mean_all >= 2.0)
            or (fraction_marked >= 0.45)
        )

        if is_full_gen:
            label = "AI-generated"
            has_ai_label = True
            display_fraction = fraction_marked  # fraction of detected tiles
        else:
            # Region edit: percentage = detected tile count / total tiles
            # (tiles_marked is the ground truth here; bbox_coverage would over-estimate)
            pct = max(1, round(fraction_marked * 100))
            label = f"AI-edited: {pct}% of image"
            has_ai_label = True
            display_fraction = fraction_marked
    else:
        label = "No AI watermark"
        has_ai_label = False
        display_fraction = 0.0

    return {
        "mode": "truthlens",
        "label": label,
        "has_ai_label": has_ai_label,
        "fraction_marked": float(fraction_marked),   # raw watermark tile fraction
        "display_fraction": display_fraction,         # fraction shown in UI label
        "tiles_marked": tiles_marked,
        "total_tiles": total_tiles,
        "global_z": float(global_z),
        "crop_offset": offset,
        "z_matrix": z_matrix,
        "provenance_status": prov_status,
        "provenance_details": prov_reason,
        "metadata_present": metadata_present,
        "manifest": manifest_obj
    }
