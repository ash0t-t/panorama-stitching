import argparse
import sys
import time
import cv2

from analyzer import analyze_images, select_algorithm
from features import create_detector, detect_and_compute, match_features, find_homography
from stitcher import stitch

def parse_args():
    parser = argparse.ArgumentParser(
        description="Panorama stitcher — automatically selects the best algorithm."
    )
    parser.add_argument("left",  help="Path to the LEFT (query) image")
    parser.add_argument("right", help="Path to the RIGHT (reference) image")
    parser.add_argument("--output", "-o", default="panorama.jpg",
                        help="Output file path (default: panorama.jpg)")
    parser.add_argument("--algo", "-a", default=None,
                        choices=["ORB", "SURF", "SIFT"],
                        help="Force a specific algorithm instead of auto-selection")
    parser.add_argument("--show", "-s", action="store_true",
                        help="Display the panorama in a window after saving")
    parser.add_argument("--min-matches", type=int, default=10,
                        help="Minimum good matches required (default: 10)")
    return parser.parse_args()

def run(args):
    print(f"\n{'='*60}")
    print("  DRONE PANORAMA STITCHER")
    print(f"{'='*60}")
    print(f"\n[1/5] Loading images...")
    img1 = cv2.imread(args.left)
    img2 = cv2.imread(args.right)

    if img1 is None:
        sys.exit(f"[ERROR] Cannot read image: {args.left}")
    if img2 is None:
        sys.exit(f"[ERROR] Cannot read image: {args.right}")

    print(f"      Left  : {args.left}  ({img1.shape[1]}×{img1.shape[0]}px)")
    print(f"      Right : {args.right}  ({img2.shape[1]}×{img2.shape[0]}px)")

    print(f"\n[2/5] Analyzing image properties...")
    metrics = analyze_images(img1, img2)
    print(f"      Avg brightness  : {metrics['avg_brightness']:.1f}  (0–255)")
    print(f"      Avg contrast    : {metrics['avg_contrast']:.1f}  (std-dev)")
    print(f"      Avg blur score  : {metrics['avg_blur_score']:.1f}  (Laplacian var)")
    print(f"      Avg texture     : {metrics['avg_texture']:.4f} (edge density)")
    print(f"      Avg resolution  : {metrics['avg_megapixels']:.2f} MP")
    print(f"      Overlap score   : {metrics['overlap_score']:.4f}")

    if args.algo:
        algorithm = args.algo.upper()
        reason = "manually specified by user"
    else:
        algorithm, reason = select_algorithm(metrics)

    print(f"\n[3/5] Algorithm selection → \033[1;32m{algorithm}\033[0m")
    print(f"      Reason: {reason}")

    print(f"\n[4/5] Detecting and matching features with {algorithm}...")
    detector = create_detector(algorithm)

    t0 = time.perf_counter()
    kps1, desc1 = detect_and_compute(detector, img1)
    kps2, desc2 = detect_and_compute(detector, img2)
    t_detect = time.perf_counter() - t0

    print(f"      Keypoints found : {len(kps1)} (left) | {len(kps2)} (right)")
    print(f"      Detection time  : {t_detect*1000:.1f} ms")

    if desc1 is None or desc2 is None or len(kps1) == 0 or len(kps2) == 0:
        sys.exit("[ERROR] No descriptors found. Images may be too uniform or too blurry.")

    t0 = time.perf_counter()
    good_matches = match_features(algorithm, desc1, desc2)
    t_match = time.perf_counter() - t0

    print(f"      Good matches    : {len(good_matches)}")
    print(f"      Matching time   : {t_match*1000:.1f} ms")

    if len(good_matches) < args.min_matches:
        sys.exit(
            f"[ERROR] Only {len(good_matches)} good matches found "
            f"(need ≥{args.min_matches}). "
            "Try images with more overlap or use --algo SIFT."
        )

    H, mask = find_homography(kps1, kps2, good_matches, min_matches=args.min_matches)
    if H is None:
        sys.exit("[ERROR] Could not compute homography. "
                 "Increase overlap between the images.")

    inliers = int(mask.sum()) if mask is not None else 0
    print(f"      Inliers (RANSAC): {inliers} / {len(good_matches)}")

    if H[0, 2] > img2.shape[1] * 0.3:
        print("      [INFO] Images appear to be in reverse order — swapping left/right.")
        img1, img2 = img2, img1
        kps1, kps2 = kps2, kps1
        desc1, desc2 = desc2, desc1
        good_matches = match_features(algorithm, desc1, desc2)
        H, mask = find_homography(kps1, kps2, good_matches, min_matches=args.min_matches)
        if H is None:
            sys.exit("[ERROR] Homography failed after swap too.")

    print(f"\n[5/5] Stitching panorama...")
    t0 = time.perf_counter()
    try:
        panorama = stitch(img1, img2, H)
    except ValueError as e:
        sys.exit(f"[ERROR] {e}")
    t_stitch = time.perf_counter() - t0
    print(f"      Stitch time     : {t_stitch*1000:.1f} ms")
    print(f"      Output size     : {panorama.shape[1]}×{panorama.shape[0]}px")

    cv2.imwrite(args.output, panorama)
    print(f"\nPanorama saved → {args.output}")
    print(f"{'='*60}\n")

    if args.show:
        max_display_w = 1400
        disp = panorama
        if panorama.shape[1] > max_display_w:
            scale = max_display_w / panorama.shape[1]
            disp = cv2.resize(panorama, None, fx=scale, fy=scale)
        cv2.imshow("Panorama — press any key to close", disp)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run(parse_args())