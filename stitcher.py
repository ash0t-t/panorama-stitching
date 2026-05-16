import cv2
import numpy as np

def stitch(img1: np.ndarray, img2: np.ndarray, H: np.ndarray) -> np.ndarray:
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    corners1 = np.float32([[0, 0], [w1, 0], [w1, h1], [0, h1]]).reshape(-1, 1, 2)
    corners1_in2 = cv2.perspectiveTransform(corners1, H)

    corners2 = np.float32([[0, 0], [w2, 0], [w2, h2], [0, h2]]).reshape(-1, 1, 2)

    all_corners = np.concatenate([corners1_in2, corners2], axis=0)

    x_min = np.floor(all_corners[:, 0, 0].min()).astype(int)
    y_min = np.floor(all_corners[:, 0, 1].min()).astype(int)
    x_max = np.ceil(all_corners[:, 0, 0].max()).astype(int)
    y_max = np.ceil(all_corners[:, 0, 1].max()).astype(int)

    tx = max(0, -x_min)
    ty = max(0, -y_min)

    canvas_w = x_max + tx
    canvas_h = y_max + ty

    MAX_DIM = 16_000
    if canvas_w > MAX_DIM or canvas_h > MAX_DIM or canvas_w <= 0 or canvas_h <= 0:
        raise ValueError(
            f"Computed canvas size {canvas_w}x{canvas_h} is unreasonable. "
            "The homography may be degenerate — try images with more overlap."
        )

    T = np.array([[1, 0, tx],
                  [0, 1, ty],
                  [0, 0,  1]], dtype=np.float64)

    warped1 = cv2.warpPerspective(img1, T @ H, (canvas_w, canvas_h))

    img2_x = tx
    img2_y = ty

    canvas = warped1.copy()
    y2_end = min(img2_y + h2, canvas_h)
    x2_end = min(img2_x + w2, canvas_w)
    canvas[img2_y:y2_end, img2_x:x2_end] = img2[:y2_end - img2_y, :x2_end - img2_x]

    canvas = _gradient_blend(warped1, img2, canvas, img2_x, img2_y,
                             y2_end, x2_end)

    return _crop_black_borders(canvas)

def _gradient_blend(warped1: np.ndarray, img2: np.ndarray,
                    canvas: np.ndarray,
                    img2_x: int, img2_y: int,
                    y2_end: int, x2_end: int) -> np.ndarray:
    ch, cw = canvas.shape[:2]

    gray_w1 = cv2.cvtColor(warped1, cv2.COLOR_BGR2GRAY)
    mask1 = (gray_w1 > 0).astype(np.float32)

    mask2 = np.zeros((ch, cw), dtype=np.float32)
    mask2[img2_y:y2_end, img2_x:x2_end] = 1.0

    overlap = mask1 * mask2

    if overlap.sum() == 0:
        return canvas

    overlap_cols = np.where(overlap.max(axis=0) > 0)[0]
    if len(overlap_cols) == 0:
        return canvas

    ol_x_start = int(overlap_cols.min())
    ol_x_end   = int(overlap_cols.max()) + 1
    ol_width   = ol_x_end - ol_x_start

    alpha = np.zeros((ch, cw), dtype=np.float32)
    if ol_width > 1:
        ramp = np.linspace(0.0, 1.0, ol_width, dtype=np.float32)
        alpha[:, ol_x_start:ol_x_end] = ramp[np.newaxis, :]
    alpha[:, ol_x_end:] = 1.0

    img2_layer = np.zeros((ch, cw, 3), dtype=np.float32)
    img2_layer[img2_y:y2_end, img2_x:x2_end] = \
        img2[:y2_end - img2_y, :x2_end - img2_x].astype(np.float32)

    w1_layer  = warped1.astype(np.float32)
    canvas_f  = canvas.astype(np.float32)
    bm        = overlap[:, :, np.newaxis]
    a         = alpha[:, :, np.newaxis]

    blended = np.where(
        bm > 0,
        (1.0 - a) * w1_layer + a * img2_layer,
        canvas_f
    )

    return np.clip(blended, 0, 255).astype(np.uint8)


def _crop_black_borders(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return img
    x, y, w, h = cv2.boundingRect(coords)
    return img[y:y + h, x:x + w]