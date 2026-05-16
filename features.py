import cv2
import numpy as np

def create_detector(algorithm: str):
    algo = algorithm.upper()
    if algo == "ORB":
        return cv2.ORB_create(nfeatures=3000)
    elif algo == "SIFT":
        return cv2.SIFT_create()
    elif algo == "SURF":
        try:
            det = cv2.xfeatures2d.SURF_create(400)
            det.detect(np.zeros((8, 8), dtype=np.uint8))
            return det
        except (AttributeError, cv2.error):
            print("[WARNING] SURF is not available in this OpenCV build "
                  "(patent-protected; needs OPENCV_ENABLE_NONFREE). "
                  "Falling back to SIFT.")
            return cv2.SIFT_create()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm!r}. Choose ORB, SURF, or SIFT.")


def detect_and_compute(detector, img: np.ndarray):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kps, descs = detector.detectAndCompute(gray, None)
    return kps, descs


def match_features(algorithm: str, desc1: np.ndarray, desc2: np.ndarray,
                   ratio_thresh: float = 0.70) -> list:
    algo = algorithm.upper()
    use_binary = algo == "ORB"

    if use_binary:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    else:
        FLANN_INDEX_KDTREE = 1
        index_params  = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
        desc1 = desc1.astype(np.float32)
        desc2 = desc2.astype(np.float32)

    raw_matches = matcher.knnMatch(desc1, desc2, k=2)

    good = []
    for pair in raw_matches:
        if len(pair) == 2:
            m, n = pair
            if m.distance < ratio_thresh * n.distance:
                good.append(m)

    return good

def find_homography(kps1, kps2, good_matches: list,
                    min_matches: int = 10) -> tuple[np.ndarray | None, np.ndarray | None]:
    if len(good_matches) < min_matches:
        return None, None

    src_pts = np.float32([kps1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kps2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H, mask