# Drone Panorama Stitcher

Automatically stitches **two overlapping images** into a single panorama by:

1. Analyzing the image pair (brightness, contrast, resolution, blur, texture)
2. Selecting the best feature-detection algorithm (ORB / SURF / SIFT)
3. Detecting and matching keypoints
4. Computing a homography (RANSAC)
5. Warping + gradient-blending → cropped panorama

---

## Project structure

```
panorama_stitcher/
├── main.py          ← Entry point / CLI
├── analyzer.py      ← Image analysis + algorithm selection logic
├── features.py      ← Feature detection, description, matching, homography
├── stitcher.py      ← Warping, gradient blending, border cropping
├── requirements.txt
└── README.md
```

---

## Requirements

| Software | Minimum version |
|----------|----------------|
| Python   | 3.10+          |
| pip      | any recent     |

> **Note:** The project uses `opencv-contrib-python` which includes **SURF**
> (in the `xfeatures2d` module). However, SURF is patent-protected and
> **disabled in most pre-built binaries** — even from `opencv-contrib-python`.
> If SURF is unavailable at runtime the code automatically falls back to SIFT;
> you will see a warning line but the program continues normally.

---

## Installation

### 1. Clone / download the project

```bash
git clone <your-repo-url>
cd panorama_stitcher
```

Or just copy the four `.py` files into a folder.

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Activate — macOS / Linux:
source .venv/bin/activate

# Activate — Windows (cmd):
.venv\Scripts\activate.bat

# Activate — Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> This installs `opencv-contrib-python` (≈ 90 MB) and `numpy`.

---

## Usage

### Basic (auto-select algorithm)

```bash
python main.py left.jpg right.jpg
```

Output is saved as `panorama.jpg` in the current directory.

### Specify output path

```bash
python main.py left.jpg right.jpg --output my_panorama.jpg
```

### Also display the result in a window

```bash
python main.py left.jpg right.jpg --show
```

### Force a specific algorithm

```bash
python main.py left.jpg right.jpg --algo SIFT
python main.py left.jpg right.jpg --algo ORB
python main.py left.jpg right.jpg --algo SURF
```

### All options

```
python main.py --help

positional arguments:
  left                  Path to the LEFT (query) image
  right                 Path to the RIGHT (reference) image

optional arguments:
  -o, --output PATH     Output file path (default: panorama.jpg)
  -a, --algo {ORB,SURF,SIFT}
                        Force a specific algorithm (default: auto)
  -s, --show            Display result window after saving
  --min-matches N       Min good matches required (default: 10)
```

> **Image order:** Pass the left image first and the right image second.
> The program will detect if they appear to be swapped and correct the
> order automatically, printing an `[INFO]` line if it does so.

---

## Algorithm selection logic

| Condition | Chosen algorithm | Reason |
|-----------|-----------------|--------|
| Brightness < 60 **or** contrast < 30 | **SIFT** | Best illumination robustness |
| Blur score (Laplacian) < 50 | **SIFT** | Robust to image degradation |
| Resolution > 4 MP, bright, texture-rich | **ORB** | Speed, low memory footprint |
| Everything else | **SURF** → SIFT fallback | Best speed / accuracy trade-off |

You can always override with `--algo`.

---

## Algorithm comparison

| Property | ORB | SURF | SIFT |
|----------|-----|------|------|
| Speed (1 MP image) | 10–30 ms | 80–150 ms | 120–300 ms |
| Keypoints | 500–2000 | 1000–3000 | 1500–4000 |
| Matching accuracy | 40–70 % | 60–85 % | 70–90 % |
| Rotation invariance | 0.9 | 0.95 | 0.98 |
| Scale invariance | 0.6 | 0.85 | 0.95 |
| Illumination robustness | 0.6 | 0.8 | 0.9 |
| Descriptor size | 32 B | 64 B | 128 B |

Lowe's ratio test threshold is set to **0.70** (stricter than the common
0.75) to reduce false matches and improve homography stability.

---

## How blending works

The overlap zone between the two images is blended with a **horizontal
gradient** rather than a hard cut or flat 50/50 mix:

```
warped img1 ──────────────────────────┐
                              overlap  │ gradient 0 → 1
                        img2 ──────────┘
```

- Left of overlap → 100 % warped img1
- Inside overlap → linear ramp from img1 to img2
- Right of overlap → 100 % img2

This eliminates visible seams even when the two images have slightly
different exposures or colour temperatures.

---

## Example console output

```
============================================================
  DRONE PANORAMA STITCHER
============================================================

[1/5] Loading images...
      Left  : left.png  (596×520px)
      Right : right.png  (596×520px)

[2/5] Analyzing image properties...
      Avg brightness  : 87.2  (0–255)
      Avg contrast    : 53.2  (std-dev)
      Avg blur score  : 113.0  (Laplacian var)
      Avg texture     : 0.1006 (edge density)
      Avg resolution  : 0.31 MP
      Overlap score   : 0.8627

[3/5] Algorithm selection → SURF
      Reason: balanced conditions (brightness=87.2, contrast=53.2, 0.3 MP) → SURF chosen as the best trade-off

[4/5] Detecting and matching features with SURF...
[WARNING] SURF is not available in this OpenCV build (patent-protected; needs OPENCV_ENABLE_NONFREE). Falling back to SIFT.
      Keypoints found : 1821 (left) | 1654 (right)
      Detection time  : 187.3 ms
      Good matches    : 312
      Matching time   : 14.6 ms
      Inliers (RANSAC): 289 / 312

[5/5] Stitching panorama...
      Stitch time     : 38.1 ms
      Output size     : 891×520px

Panorama saved → panorama.jpg
============================================================
```

---

## Troubleshooting

| Error / symptom | Fix |
|-----------------|-----|
| `Cannot read image` | Check the file path; use quotes if it contains spaces |
| `Only N good matches found` | Images need more overlap (~30 %), or use `--algo SIFT` |
| `Could not compute homography` | Same as above — increase overlap |
| SURF warning, falls back to SIFT | Expected — SURF is patent-locked in pre-built OpenCV; SIFT is used instead |
| Canvas size unreasonable error | Homography is degenerate; ensure images have real overlap and are not too similar overall |
| Black bands in output | Normal for strong perspective difference; try `--algo SIFT` for more keypoints |

---

## Tips for best results

* **Overlap**: aim for 30–50 % horizontal overlap between the two shots.
* **Same exposure**: keep ISO / shutter consistent between frames — the gradient blend handles small differences but not large ones.
* **Pass images in order**: left image first, right image second (the program auto-detects swaps but explicit order is cleaner).
* **Straight flight path**: the less the drone tilts or rolls, the better the homography fit.
* **High texture scenes** work best; plain skies or flat walls produce very few keypoints.


---

## Project structure

```
panorama_stitcher/
├── main.py          ← Entry point / CLI
├── analyzer.py      ← Image analysis + algorithm selection logic
├── features.py      ← Feature detection, description, matching, homography
├── stitcher.py      ← Warping, blending, border cropping
├── requirements.txt
└── README.md
```

---

## Requirements

| Software | Minimum version |
|----------|----------------|
| Python   | 3.10+          |
| pip      | any recent     |

> **Note:** The project uses `opencv-contrib-python` which includes **SURF**
> (in the `xfeatures2d` module). If you install plain `opencv-python`, SURF
> will not be available and the code will automatically fall back to SIFT.

---

## Installation

### 1. Clone / download the project

```bash
git clone <your-repo-url>
cd panorama_stitcher
```

Or just copy the four `.py` files into a folder.

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Activate — macOS / Linux:
source .venv/bin/activate

# Activate — Windows (cmd):
.venv\Scripts\activate.bat

# Activate — Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> This installs `opencv-contrib-python` (≈ 90 MB) and `numpy`.

---

## Usage

### Basic (auto-select algorithm)

```bash
python main.py left.jpg right.jpg
```

Output is saved as `panorama.jpg` in the current directory.

### Specify output path

```bash
python main.py left.jpg right.jpg --output my_panorama.jpg
```

### Also display the result in a window

```bash
python main.py left.jpg right.jpg --show
```

### Force a specific algorithm

```bash
python main.py left.jpg right.jpg --algo SIFT
python main.py left.jpg right.jpg --algo ORB
python main.py left.jpg right.jpg --algo SURF
```

### All options

```
python main.py --help

positional arguments:
  left                  Path to the LEFT (query) image
  right                 Path to the RIGHT (reference) image

optional arguments:
  -o, --output PATH     Output file path (default: panorama.jpg)
  -a, --algo {ORB,SURF,SIFT}
                        Force a specific algorithm (default: auto)
  -s, --show            Display result window after saving
  --min-matches N       Min good matches required (default: 10)
```

---

## Algorithm selection logic

| Condition | Chosen algorithm | Reason |
|-----------|-----------------|--------|
| Brightness < 60 **or** contrast < 30 | **SIFT** | Best illumination robustness |
| Blur score (Laplacian) < 50 | **SIFT** | Robust to image degradation |
| Resolution > 4 MP, bright, texture-rich | **ORB** | Speed, low memory footprint |
| Everything else | **SURF** | Best speed / accuracy trade-off |

You can override with `--algo`.

---

## Algorithm comparison

| Property | ORB | SURF | SIFT |
|----------|-----|------|------|
| Speed (1 MP image) | 10–30 ms | 80–150 ms | 120–300 ms |
| Keypoints | 500–2000 | 1000–3000 | 1500–4000 |
| Matching accuracy | 40–70 % | 60–85 % | 70–90 % |
| Rotation invariance | 0.9 | 0.95 | 0.98 |
| Scale invariance | 0.6 | 0.85 | 0.95 |
| Illumination robustness | 0.6 | 0.8 | 0.9 |
| Descriptor size | 32 B | 64 B | 128 B |

---

## Example console output

```
============================================================
  DRONE PANORAMA STITCHER
============================================================

[1/5] Loading images...
      Left  : left.jpg  (3840×2160px)
      Right : right.jpg  (3840×2160px)

[2/5] Analyzing image properties...
      Avg brightness  : 112.4  (0–255)
      Avg contrast    : 48.7  (std-dev)
      Avg blur score  : 321.0  (Laplacian var)
      Avg texture     : 0.0821 (edge density)
      Avg resolution  : 8.29 MP
      Overlap score   : 0.9412

[3/5] Algorithm selection → ORB
      Reason: high-res (8.3 MP), well-lit (112.4), texture-rich (0.082) → ORB chosen for speed

[4/5] Detecting and matching features with ORB...
      Keypoints found : 2847 (left) | 2901 (right)
      Detection time  : 23.4 ms
      Good matches    : 438
      Matching time   : 8.1 ms
      Inliers (RANSAC): 412 / 438

[5/5] Stitching panorama...
      Stitch time     : 55.2 ms
      Output size     : 6914×2160px

Panorama saved → panorama.jpg
============================================================
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Cannot read image` | Check the file path; use quotes if it contains spaces |
| `Only N good matches found` | Images need more overlap (~30 %), or use `--algo SIFT` |
| `Could not compute homography` | Same as above — increase overlap |
| SURF not available | Install `opencv-contrib-python` (not plain `opencv-python`) |
| Black bands in output | Normal for extreme perspective changes; try `--algo SIFT` |

---

## Tips for best results

* **Overlap**: aim for 30–50 % horizontal overlap between the two shots.
* **Same exposure**: keep ISO / shutter consistent between frames.
* **Straight flight path**: the less the drone tilts, the better the homography fit.
* **High texture scenes** work best; plain skies or flat walls have few keypoints.