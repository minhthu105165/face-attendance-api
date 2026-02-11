import cv2
import numpy as np


def blur_score(bgr: np.ndarray) -> float:
    """Variance of Laplacian: càng cao càng nét."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def clamp_bbox_xyxy(x1, y1, x2, y2, W, H):
    x1 = max(0, min(int(x1), W - 1))
    y1 = max(0, min(int(y1), H - 1))
    x2 = max(0, min(int(x2), W))
    y2 = max(0, min(int(y2), H))
    return x1, y1, x2, y2


def quality_gate(img_bgr: np.ndarray, face, min_conf=0.6, min_face=40, min_blur=60.0):
    """
    Return (ok: bool, meta: dict).
    meta gồm w,h,conf,blur để debug.
    """
    conf = getattr(face, "confidence", None)
    if conf is not None and conf < min_conf:
        return False, {"reason": "lowconf", "conf": float(conf)}

    b = getattr(face, "bbox_xyxy", None)
    if b is None:
        b = getattr(face, "bbox", None)
    if b is None:
        # không có bbox -> cho qua (hiếm)
        return True, {"reason": "nobbox", "conf": float(conf) if conf is not None else None}

    if hasattr(b, "tolist"):
        b = b.tolist()
    x1, y1, x2, y2 = b
    H, W = img_bgr.shape[:2]
    x1, y1, x2, y2 = clamp_bbox_xyxy(x1, y1, x2, y2, W, H)

    w = x2 - x1
    h = y2 - y1
    if w < min_face or h < min_face:
        return False, {"reason": "small", "w": w, "h": h, "conf": float(conf) if conf is not None else None}

    crop = img_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False, {"reason": "empty_crop"}

    bscore = blur_score(crop)
    if bscore < min_blur:
        return False, {"reason": "blur", "blur": float(bscore), "w": w, "h": h}

    return True, {"reason": "ok", "w": w, "h": h, "blur": float(bscore), "conf": float(conf) if conf is not None else None}
