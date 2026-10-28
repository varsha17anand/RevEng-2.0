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
| `resize_0_9x` | 100% | **50%** | 1.0% | 0.22 | `PARTIAL` |
| `resize_1_5x` | 100% | **33%** | 0.7% | 0.35 | `PARTIAL` |

### Measurable Before-vs-After Metric (For Slide 4)

> **Under standard screenshot / metadata stripping attacks:**
>
> - **Instagram AI Info Survival:** `0.0%` (Complete label bypass)
> - **TruthLens AI Detection Survival:** `100.0%` (Average Z-score: `5.5+` across marked tiles)
>
> **Under JPEG Compression (q75):**
> - **TruthLens Survival:** `100.0%` with `43%+` marked tiles and zero false positives on clean images.

### Limitations and Honest Boundary Analysis
- **Pixel Resampling (Resize 0.9x / 1.5x):** Continuous bicubic/lanczos resampling breaks the strict 8x8 block DCT frequency grid, reducing survival rate to 33–50%. This is an honest technical boundary of uncalibrated spatial DCT watermarking.
- **Adoption Pre-requisite:** TruthLens requires AI generators to embed the pixel watermark at synthesis time, serving as an immutable companion to C2PA provenance.
