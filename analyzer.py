import cv2
import numpy as np


def analyze_images(img1: np.ndarray, img2: np.ndarray) -> dict:
    metrics = {}

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    brightness1 = float(np.mean(gray1))
    brightness2 = float(np.mean(gray2))
    metrics["avg_brightness"] = (brightness1 + brightness2) / 2.0

    contrast1 = float(np.std(gray1))
    contrast2 = float(np.std(gray2))
    metrics["avg_contrast"] = (contrast1 + contrast2) / 2.0

    mp1 = (img1.shape[0] * img1.shape[1]) / 1_000_000
    mp2 = (img2.shape[0] * img2.shape[1]) / 1_000_000
    metrics["avg_megapixels"] = (mp1 + mp2) / 2.0

    blur1 = float(cv2.Laplacian(gray1, cv2.CV_64F).var())
    blur2 = float(cv2.Laplacian(gray2, cv2.CV_64F).var())
    metrics["avg_blur_score"] = (blur1 + blur2) / 2.0

    edges1 = cv2.Canny(gray1, 50, 150)
    edges2 = cv2.Canny(gray2, 50, 150)
    texture1 = float(np.count_nonzero(edges1)) / edges1.size
    texture2 = float(np.count_nonzero(edges2)) / edges2.size
    metrics["avg_texture"] = (texture1 + texture2) / 2.0

    h1, w1 = gray1.shape
    h2, w2 = gray2.shape
    strip_w = max(1, min(w1, w2) // 5)
    strip1 = gray1[:, w1 - strip_w:].astype(np.float32)
    strip2 = gray2[:, :strip_w].astype(np.float32)

    target_h = min(h1, h2)
    strip1 = cv2.resize(strip1, (strip_w, target_h))
    strip2 = cv2.resize(strip2, (strip_w, target_h))
    numer = np.sum(strip1 * strip2)
    denom = (np.linalg.norm(strip1) * np.linalg.norm(strip2)) + 1e-8
    metrics["overlap_score"] = float(numer / denom)

    return metrics


def select_algorithm(metrics: dict) -> tuple[str, str]:
    brightness = metrics["avg_brightness"]
    contrast   = metrics["avg_contrast"]
    megapixels = metrics["avg_megapixels"]
    blur       = metrics["avg_blur_score"]
    texture    = metrics["avg_texture"]

    reasons = []

    if brightness < 60 or contrast < 30:
        reasons.append(
            f"low brightness ({brightness:.1f}) or contrast ({contrast:.1f}) → "
            "SIFT chosen for superior illumination robustness"
        )
        return "SIFT", "; ".join(reasons)

    if blur < 50:
        reasons.append(
            f"blur score is low ({blur:.1f}) → "
            "SIFT chosen for robustness to image degradation"
        )
        return "SIFT", "; ".join(reasons)

    if megapixels > 4 and brightness >= 80 and texture > 0.05:
        reasons.append(
            f"high-res ({megapixels:.1f} MP), well-lit ({brightness:.1f}), "
            f"texture-rich ({texture:.3f}) → ORB chosen for speed"
        )
        return "ORB", "; ".join(reasons)

    reasons.append(
        f"balanced conditions (brightness={brightness:.1f}, contrast={contrast:.1f}, "
        f"{megapixels:.1f} MP) → SURF chosen as the best trade-off"
    )
    return "SURF", "; ".join(reasons)
