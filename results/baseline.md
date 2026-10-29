# TruthLens Baseline Benchmark

Evaluated on 6 standard sample images (512×512, 64 tiles total).

## 1. Watermark Imperceptibility (PSNR)
- **Mean PSNR:** `41.71 dB`
- **Worst-case PSNR:** `40.70 dB` (01_campus_quad.jpg)

| Sample Image | PSNR (dB) | Target (≥ 38 dB) |
|---|---|---|
| `01_campus_quad.jpg` | 40.70 dB | PASS |
| `02_portrait_student.jpg` | 42.33 dB | PASS |
| `03_city_skyline.jpg` | 41.46 dB | PASS |
| `04_coffee_scene.jpg` | 43.11 dB | PASS |
| `05_nature_lake.jpg` | 41.49 dB | PASS |
| `06_architecture_hall.jpg` | 41.17 dB | PASS |

## 2. Full-Image Tile Recall & Attack Robustness

| Attack / Transformation | Mean Recall (%) | Mean Marked Tiles | Detection Rate (≥1 tile) | Mean Latency (ms) |
|---|---|---|---|---|
| **No Attack (Identity)** | 46.4% | 29.7/64 | 6/6 | 2.0 ms |
| **Screenshot / Strip** | 46.4% | 29.7/64 | 6/6 | 23.7 ms |
| **JPEG Quality 90** | 46.4% | 29.7/64 | 6/6 | 3.8 ms |
| **JPEG Quality 75** | 43.2% | 27.7/64 | 6/6 | 3.2 ms |
| **JPEG Quality 50** | 29.9% | 19.2/64 | 6/6 | 2.8 ms |
| **Crop 10% (Odd Offset)** | 47.3% | 23.2/49 | 6/6 | 49.3 ms |
| **Crop 10% + JPEG q75** | 38.8% | 19.0/49 | 6/6 | 50.9 ms |
| **Brightness +10%** | 43.2% | 27.7/64 | 6/6 | 13.6 ms |
| **Resize 0.9x** | 0.0% | 0.0/49 | 0/6 | 56.2 ms |
| **Resize 1.5x** | 0.1% | 0.2/144 | 1/6 | 135.1 ms |
| **Resize 0.75x** | 0.0% | 0.0/36 | 0/6 | 30.7 ms |
| **Resize 1.25x** | 0.3% | 0.3/100 | 2/6 | 84.8 ms |

### Per-Sample Recall Breakdown (Key Attacks)

| Sample | No Attack | Screenshot | JPEG q75 | JPEG q50 | Resize 0.9x | Resize 1.5x |
|---|---|---|---|---|---|---|
| `01_campus_quad.jpg` | 35.9% | 35.9% | 31.2% | 28.1% | 0.0% | 0.0% |
| `02_portrait_student.jpg` | 64.1% | 64.1% | 59.4% | 51.6% | 0.0% | 0.0% |
| `03_city_skyline.jpg` | 45.3% | 45.3% | 45.3% | 25.0% | 0.0% | 0.7% |
| `04_coffee_scene.jpg` | 50.0% | 50.0% | 46.9% | 31.2% | 0.0% | 0.0% |
| `05_nature_lake.jpg` | 45.3% | 45.3% | 39.1% | 20.3% | 0.0% | 0.0% |
| `06_architecture_hall.jpg` | 37.5% | 37.5% | 37.5% | 23.4% | 0.0% | 0.0% |

## 3. False Positive Specificity (Clean Images)
- **Total Clean Test Invocations:** `72` (6 images × 12 transformations)
- **Total False Positive Tiles Flagged:** `3`
- **False Positive Rate:** `0.0417%`

| Attack on Clean Image | Total False Positive Tiles Flagged | Clean Images With 0 FP |
|---|---|---|
| No Attack (Identity) | 0 | 6/6 |
| Screenshot / Strip | 0 | 6/6 |
| JPEG Quality 90 | 0 | 6/6 |
| JPEG Quality 75 | 0 | 6/6 |
| JPEG Quality 50 | 0 | 6/6 |
| Crop 10% (Odd Offset) | 0 | 6/6 |
| Crop 10% + JPEG q75 | 0 | 6/6 |
| Brightness +10% | 0 | 6/6 |
| Resize 0.9x | 0 | 6/6 |
| Resize 1.5x | 1 | 5/6 |
| Resize 0.75x | 0 | 6/6 |
| Resize 1.25x | 2 | 4/6 |

## 4. Localized Region AI Edit Detection

### 4-Tile Edit (Target: 4 tiles)
| Sample | Screenshot Strip Label (Tiles) | JPEG q75 Label (Tiles) |
|---|---|---|
| `01_campus_quad.jpg` | AI-edited: 6% of image (4/4) | AI-edited: 6% of image (4/4) |
| `02_portrait_student.jpg` | AI-edited: 6% of image (4/4) | AI-edited: 6% of image (4/4) |
| `03_city_skyline.jpg` | AI-edited: 6% of image (4/4) | AI-edited: 6% of image (3/4) |
| `04_coffee_scene.jpg` | AI-edited: 6% of image (4/4) | AI-edited: 6% of image (4/4) |
| `05_nature_lake.jpg` | AI-edited: 5% of image (3/4) | AI-edited: 6% of image (3/4) |
| `06_architecture_hall.jpg` | AI-edited: 6% of image (4/4) | AI-edited: 6% of image (4/4) |

### 16-Tile Edit (Target: 16 tiles)
| Sample | Screenshot Strip Label (Tiles) | JPEG q75 Label (Tiles) |
|---|---|---|
| `01_campus_quad.jpg` | AI-edited: 23% of image (15/16) | AI-edited: 25% of image (15/16) |
| `02_portrait_student.jpg` | AI-edited: 25% of image (16/16) | AI-edited: 25% of image (16/16) |
| `03_city_skyline.jpg` | AI-edited: 23% of image (15/16) | AI-edited: 25% of image (14/16) |
| `04_coffee_scene.jpg` | AI-edited: 25% of image (16/16) | AI-edited: 25% of image (16/16) |
| `05_nature_lake.jpg` | AI-edited: 23% of image (15/16) | AI-edited: 25% of image (15/16) |
| `06_architecture_hall.jpg` | AI-edited: 25% of image (16/16) | AI-edited: 25% of image (16/16) |
