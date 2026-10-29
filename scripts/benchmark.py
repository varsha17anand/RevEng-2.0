"""TruthLens Comprehensive Evaluation Benchmark.

Measures:
1. PSNR of watermarked vs original across all 6 sample images.
2. Full-image tile recall (% of 64 tiles detected) under 12 attacks/transformations:
   - No attack (identity)
   - Screenshot / metadata strip
   - JPEG q90, q75, q50
   - Crop 10% (odd offset)
   - Crop 10% + JPEG q75
   - Brightness +10%
   - Resize 0.9x, 1.5x, 0.75x, 1.25x
3. Region edits (4-tile and 16-tile): label and tiles found after Screenshot and JPEG q75.
4. False positives: tiles flagged on all 6 CLEAN images under every attack (target: 0).
5. Detection timing per image.
"""

from __future__ import annotations

import glob
import io
import os
import sys
import time
from typing import Dict, List, Tuple, Any

import numpy as np
from PIL import Image, ImageEnhance

# Ensure backend is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.watermark import (
    embed_watermark,
    detect_watermark,
    compute_psnr,
    DEFAULT_BASE_STRENGTH,
    DETECTION_THRESHOLD,
    TILE_SIZE
)
from app.metadata import embed_metadata, strip_metadata, IPTC_TRAINED_ALGORITHMIC
from app.labeler import truthlens_label
from app.attacks import (
    attack_none,
    attack_screenshot_strip,
    attack_jpeg_q90,
    attack_jpeg_q75,
    attack_jpeg_q50,
    attack_crop_10_odd,
    attack_crop_jpeg_q75,
    attack_brightness_plus_10,
    attack_resize_0_9x,
    attack_resize_1_5x,
    _save_with_preserved_metadata
)
from app.ai_edit import edit_ai_region, square_crop_or_pad


def attack_resize_0_75x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Downsample image to 0.75x scale with Lanczos filtering."""
    W, H = img.size
    new_w = max(64, int(W * 0.75))
    new_h = max(64, int(H * 0.75))
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    data = _save_with_preserved_metadata(resized, img_bytes, output_format="PNG")
    return resized, data


def attack_resize_1_25x(img: Image.Image, img_bytes: bytes) -> Tuple[Image.Image, bytes]:
    """Upsample image to 1.25x scale with Lanczos filtering."""
    W, H = img.size
    new_w = int(W * 1.25)
    new_h = int(H * 1.25)
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    data = _save_with_preserved_metadata(resized, img_bytes, output_format="PNG")
    return resized, data


BENCHMARK_ATTACKS = [
    ("none", "No Attack (Identity)", attack_none),
    ("screenshot_strip", "Screenshot / Strip", attack_screenshot_strip),
    ("jpeg_q90", "JPEG Quality 90", attack_jpeg_q90),
    ("jpeg_q75", "JPEG Quality 75", attack_jpeg_q75),
    ("jpeg_q50", "JPEG Quality 50", attack_jpeg_q50),
    ("crop_10_odd", "Crop 10% (Odd Offset)", attack_crop_10_odd),
    ("crop_jpeg_q75", "Crop 10% + JPEG q75", attack_crop_jpeg_q75),
    ("brightness_plus_10", "Brightness +10%", attack_brightness_plus_10),
    ("resize_0_9x", "Resize 0.9x", attack_resize_0_9x),
    ("resize_1_5x", "Resize 1.5x", attack_resize_1_5x),
    ("resize_0_75x", "Resize 0.75x", attack_resize_0_75x),
    ("resize_1_25x", "Resize 1.25x", attack_resize_1_25x),
]


def load_sample_images() -> List[Tuple[str, Image.Image, bytes]]:
    """Load all 6 sample images, normalized to 512x512 RGB."""
    pattern = os.path.join(ROOT_DIR, "samples", "*.jpg")
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise RuntimeError(f"No sample images found at {pattern}")

    results = []
    for p in paths:
        name = os.path.basename(p)
        raw = open(p, "rb").read()
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im_norm = square_crop_or_pad(im, 512, mode="crop")
        buf = io.BytesIO()
        im_norm.save(buf, format="JPEG", quality=95)
        results.append((name, im_norm, buf.getvalue()))
    return results


def run_benchmark() -> Dict[str, Any]:
    """Execute full benchmark and return structured metrics."""
    samples = load_sample_images()
    num_samples = len(samples)

    print(f"Loaded {num_samples} sample images.")

    # 1. PSNR Evaluation
    psnr_scores = []
    watermarked_samples = []
    for name, img, raw_bytes in samples:
        wm_img = embed_watermark(img, base=DEFAULT_BASE_STRENGTH)
        psnr_val = compute_psnr(img, wm_img)
        psnr_scores.append((name, psnr_val))

        wm_bytes = embed_metadata(
            wm_img,
            digital_source_type=IPTC_TRAINED_ALGORITHMIC,
            output_format="PNG"
        )
        watermarked_samples.append((name, wm_img, wm_bytes))

    # 2. Full-Image Watermark Recall across Attacks
    # attack_key -> list of (tiles_marked, total_tiles, recall_pct, detected_bool, time_ms)
    attack_results: Dict[str, List[Dict[str, Any]]] = {k: [] for k, _, _ in BENCHMARK_ATTACKS}

    for att_key, att_label, att_fn in BENCHMARK_ATTACKS:
        for name, wm_img, wm_bytes in watermarked_samples:
            t0 = time.perf_counter()
            att_img, att_bytes = att_fn(wm_img, wm_bytes)
            res = truthlens_label(att_img, att_bytes, sync_crop=True)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            attack_results[att_key].append({
                "sample": name,
                "tiles_marked": res["tiles_marked"],
                "total_tiles": res["total_tiles"],
                "recall_pct": (res["tiles_marked"] / res["total_tiles"]) * 100 if res["total_tiles"] else 0,
                "detected": res["tiles_marked"] > 0,
                "label": res["label"],
                "time_ms": elapsed_ms
            })

    # 3. Clean Image False Positive Evaluation across all attacks
    # Clean images must have 0 false positive tiles
    clean_fp_results: Dict[str, List[int]] = {k: [] for k, _, _ in BENCHMARK_ATTACKS}
    for att_key, att_label, att_fn in BENCHMARK_ATTACKS:
        for name, clean_img, clean_bytes in samples:
            att_img, att_bytes = att_fn(clean_img, clean_bytes)
            res = truthlens_label(att_img, att_bytes, sync_crop=True)
            clean_fp_results[att_key].append(res["tiles_marked"])

    # 4. Region Edit Evaluation (4-tile and 16-tile edits)
    # 4-tile: (128, 128, 256, 256), 16-tile: (128, 128, 384, 384)
    region_results = {
        "4_tile": {"screenshot": [], "jpeg_q75": []},
        "16_tile": {"screenshot": [], "jpeg_q75": []}
    }

    for name, clean_img, clean_bytes in samples:
        # 4-tile edit
        ed4_img, ed4_bytes, _, _ = edit_ai_region(clean_img, (128, 128, 256, 256), edit_style="cyberpunk")
        # Test screenshot
        s4_img, s4_bytes = attack_screenshot_strip(ed4_img, ed4_bytes)
        res_s4 = truthlens_label(s4_img, s4_bytes, sync_crop=True)
        region_results["4_tile"]["screenshot"].append({
            "sample": name,
            "label": res_s4["label"],
            "tiles_marked": res_s4["tiles_marked"],
            "total_tiles": res_s4["total_tiles"]
        })
        # Test jpeg_q75
        j4_img, j4_bytes = attack_jpeg_q75(ed4_img, ed4_bytes)
        res_j4 = truthlens_label(j4_img, j4_bytes, sync_crop=True)
        region_results["4_tile"]["jpeg_q75"].append({
            "sample": name,
            "label": res_j4["label"],
            "tiles_marked": res_j4["tiles_marked"],
            "total_tiles": res_j4["total_tiles"]
        })

        # 16-tile edit
        ed16_img, ed16_bytes, _, _ = edit_ai_region(clean_img, (128, 128, 384, 384), edit_style="cyberpunk")
        # Test screenshot
        s16_img, s16_bytes = attack_screenshot_strip(ed16_img, ed16_bytes)
        res_s16 = truthlens_label(s16_img, s16_bytes, sync_crop=True)
        region_results["16_tile"]["screenshot"].append({
            "sample": name,
            "label": res_s16["label"],
            "tiles_marked": res_s16["tiles_marked"],
            "total_tiles": res_s16["total_tiles"]
        })
        # Test jpeg_q75
        j16_img, j16_bytes = attack_jpeg_q75(ed16_img, ed16_bytes)
        res_j16 = truthlens_label(j16_img, j16_bytes, sync_crop=True)
        region_results["16_tile"]["jpeg_q75"].append({
            "sample": name,
            "label": res_j16["label"],
            "tiles_marked": res_j16["tiles_marked"],
            "total_tiles": res_j16["total_tiles"]
        })

    return {
        "psnr_scores": psnr_scores,
        "attack_results": attack_results,
        "clean_fp_results": clean_fp_results,
        "region_results": region_results,
    }


def format_markdown(data: Dict[str, Any], title: str = "TruthLens Baseline Benchmark") -> str:
    """Format benchmark data into clean Markdown."""
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Evaluated on {len(data['psnr_scores'])} standard sample images (512×512, 64 tiles total).")
    lines.append("")

    # 1. PSNR Section
    psnr_vals = [score for _, score in data["psnr_scores"]]
    mean_psnr = np.mean(psnr_vals)
    min_psnr = np.min(psnr_vals)
    worst_img = min(data["psnr_scores"], key=lambda x: x[1])[0]

    lines.append("## 1. Watermark Imperceptibility (PSNR)")
    lines.append(f"- **Mean PSNR:** `{mean_psnr:.2f} dB`")
    lines.append(f"- **Worst-case PSNR:** `{min_psnr:.2f} dB` ({worst_img})")
    lines.append("")
    lines.append("| Sample Image | PSNR (dB) | Target (≥ 38 dB) |")
    lines.append("|---|---|---|")
    for name, score in data["psnr_scores"]:
        lines.append(f"| `{name}` | {score:.2f} dB | {'PASS' if score >= 38.0 else 'FAIL'} |")
    lines.append("")

    # 2. Full-Image Watermark Tile Recall across Attacks
    lines.append("## 2. Full-Image Tile Recall & Attack Robustness")
    lines.append("")
    lines.append("| Attack / Transformation | Mean Recall (%) | Mean Marked Tiles | Detection Rate (≥1 tile) | Mean Latency (ms) |")
    lines.append("|---|---|---|---|---|")

    attack_name_map = {k: lbl for k, lbl, _ in BENCHMARK_ATTACKS}

    for att_key, _, _ in BENCHMARK_ATTACKS:
        records = data["attack_results"][att_key]
        recalls = [r["recall_pct"] for r in records]
        tiles = [r["tiles_marked"] for r in records]
        detected = [r["detected"] for r in records]
        times = [r["time_ms"] for r in records]

        m_rec = np.mean(recalls)
        m_tiles = np.mean(tiles)
        tot_tiles = records[0]["total_tiles"]
        det_rate = f"{sum(detected)}/{len(detected)}"
        m_time = np.mean(times)

        lines.append(
            f"| **{attack_name_map[att_key]}** | {m_rec:.1f}% | {m_tiles:.1f}/{tot_tiles} | {det_rate} | {m_time:.1f} ms |"
        )
    lines.append("")

    # Detailed per-image breakdown for Key Targets
    lines.append("### Per-Sample Recall Breakdown (Key Attacks)")
    lines.append("")
    lines.append("| Sample | No Attack | Screenshot | JPEG q75 | JPEG q50 | Resize 0.9x | Resize 1.5x |")
    lines.append("|---|---|---|---|---|---|---|")
    for i in range(len(data["psnr_scores"])):
        sample_name = data["psnr_scores"][i][0]
        r_none = data["attack_results"]["none"][i]["recall_pct"]
        r_sc = data["attack_results"]["screenshot_strip"][i]["recall_pct"]
        r_q75 = data["attack_results"]["jpeg_q75"][i]["recall_pct"]
        r_q50 = data["attack_results"]["jpeg_q50"][i]["recall_pct"]
        r_r09 = data["attack_results"]["resize_0_9x"][i]["recall_pct"]
        r_r15 = data["attack_results"]["resize_1_5x"][i]["recall_pct"]
        lines.append(
            f"| `{sample_name}` | {r_none:.1f}% | {r_sc:.1f}% | {r_q75:.1f}% | {r_q50:.1f}% | {r_r09:.1f}% | {r_r15:.1f}% |"
        )
    lines.append("")

    # 3. Clean Image False Positives
    lines.append("## 3. False Positive Specificity (Clean Images)")
    total_clean_tests = 0
    total_fp_tiles = 0
    for att_key, _, _ in BENCHMARK_ATTACKS:
        fp_list = data["clean_fp_results"][att_key]
        total_clean_tests += len(fp_list)
        total_fp_tiles += sum(fp_list)

    lines.append(f"- **Total Clean Test Invocations:** `{total_clean_tests}` ({len(data['psnr_scores'])} images × 12 transformations)")
    lines.append(f"- **Total False Positive Tiles Flagged:** `{total_fp_tiles}`")
    lines.append(f"- **False Positive Rate:** `{0.0 if total_fp_tiles == 0 else (total_fp_tiles/total_clean_tests):.4f}%`")
    lines.append("")
    lines.append("| Attack on Clean Image | Total False Positive Tiles Flagged | Clean Images With 0 FP |")
    lines.append("|---|---|---|")
    for att_key, _, _ in BENCHMARK_ATTACKS:
        fp_list = data["clean_fp_results"][att_key]
        n_pass = sum(1 for fp in fp_list if fp == 0)
        lines.append(f"| {attack_name_map[att_key]} | {sum(fp_list)} | {n_pass}/{len(fp_list)} |")
    lines.append("")

    # 4. Region Edit Results
    lines.append("## 4. Localized Region AI Edit Detection")
    lines.append("")
    lines.append("### 4-Tile Edit (Target: 4 tiles)")
    lines.append("| Sample | Screenshot Strip Label (Tiles) | JPEG q75 Label (Tiles) |")
    lines.append("|---|---|---|")
    for i in range(len(data["psnr_scores"])):
        sample_name = data["psnr_scores"][i][0]
        sc_res = data["region_results"]["4_tile"]["screenshot"][i]
        j75_res = data["region_results"]["4_tile"]["jpeg_q75"][i]
        lines.append(
            f"| `{sample_name}` | {sc_res['label']} ({sc_res['tiles_marked']}/4) | {j75_res['label']} ({j75_res['tiles_marked']}/4) |"
        )
    lines.append("")

    lines.append("### 16-Tile Edit (Target: 16 tiles)")
    lines.append("| Sample | Screenshot Strip Label (Tiles) | JPEG q75 Label (Tiles) |")
    lines.append("|---|---|---|")
    for i in range(len(data["psnr_scores"])):
        sample_name = data["psnr_scores"][i][0]
        sc_res = data["region_results"]["16_tile"]["screenshot"][i]
        j75_res = data["region_results"]["16_tile"]["jpeg_q75"][i]
        lines.append(
            f"| `{sample_name}` | {sc_res['label']} ({sc_res['tiles_marked']}/16) | {j75_res['label']} ({j75_res['tiles_marked']}/16) |"
        )
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("Starting TruthLens Benchmark Run...")
    print("=" * 60)
    data = run_benchmark()
    md = format_markdown(data, title="TruthLens Baseline Benchmark")

    out_path = os.path.join(ROOT_DIR, "results", "baseline.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(md)

    print(f"\nBenchmark completed successfully! Saved to {out_path}\n")
    print(md[:1500])

