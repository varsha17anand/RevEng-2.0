# TruthLens vs Instagram AI-Info Robustness Report

Evaluation conducted on 6 diverse photographic samples (campus quad, portrait, city skyline, cafe, nature lake, architecture hall).

### Core Watermark Fidelity & False Positive Metrics
- **Mean PSNR:** `41.71 dB` (imperceptibility standard ≥ 40 dB: **PASS**)
- **Min PSNR:** `40.70 dB`
- **Clean Images False Positive Tiles:** `0 / 384` (`0.00%`)
- **Clean Images Max Z-Score:** `2.93` (detection threshold: `4.0`)

### Attack Robustness Comparison Table

| Attack Transformation | Instagram Mode (Metadata) | TruthLens Mode (DCT Watermark) | Avg Tiles Marked | Avg Z-Score | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `none` | 100% | **100%** | 46.4% | 5.15 | `SURVIVED` |
| `screenshot_strip` | 0% | **100%** | 46.4% | 5.15 | `SURVIVED` |
| `jpeg_q90` | 100% | **100%** | 46.4% | 5.08 | `SURVIVED` |
| `jpeg_q75` | 100% | **100%** | 43.2% | 4.27 | `SURVIVED` |
| `jpeg_q50` | 100% | **100%** | 29.9% | 3.21 | `SURVIVED` |
| `crop_10_odd` | 100% | **100%** | 47.3% | 5.12 | `SURVIVED` |
| `crop_jpeg_q75` | 100% | **100%** | 38.8% | 4.14 | `SURVIVED` |
| `brightness_plus_10` | 100% | **100%** | 43.2% | 5.00 | `SURVIVED` |
| `resize_0_9x` | 100% | **0%** | 0.0% | -0.05 | `DEFEATED` |
| `resize_1_5x` | 100% | **17%** | 0.1% | 0.24 | `PARTIAL` |

### Key Empirical Findings

> **Under standard screenshot / metadata stripping attacks:**
>
> - **Instagram AI Info Survival:** `0.0%` (Complete label bypass)
> - **TruthLens AI Detection Survival:** `100.0%` (Average Z-score: `5.5+` across marked tiles)
>
> **Under JPEG Compression (q75):**
> - **TruthLens Detection Survival:** `100.0%` (avg `43.2%` tiles marked above z=4.0) with zero false positives on clean images.

### Limitations and Honest Boundary Analysis
- **Pixel Resampling (Resize 0.9x / 1.5x):** Continuous bicubic/lanczos resampling breaks the strict 8x8 block DCT frequency grid, defeating uncalibrated spatial DCT tile detection (0–17% survival in Attack Lab). This is a documented technical boundary of uncalibrated spatial DCT watermarking.
- **Adoption Pre-requisite:** TruthLens requires AI generators to embed the pixel watermark at synthesis time, serving as an immutable companion to C2PA provenance.
