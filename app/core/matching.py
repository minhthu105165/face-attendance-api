import numpy as np


def cosine_similarity_matrix(vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    """
    vec: (D,), mat: (N,D) đã normalize thì cosine = dot.
    """
    if mat.size == 0:
        return np.zeros((0,), dtype=np.float32)
    return mat @ vec


def best_match(vec: np.ndarray, names: list[str], gallery: np.ndarray, threshold: float):
    """
    Return (matched_name_or_None, best_score).
    """
    if gallery.size == 0 or len(names) == 0:
        return None, 0.0

    # đảm bảo normalize
    v = vec.astype(np.float32).reshape(-1)
    v = v / (np.linalg.norm(v) + 1e-9)

    sims = cosine_similarity_matrix(v, gallery.astype(np.float32))
    idx = int(np.argmax(sims))
    best = float(sims[idx])
    if best >= threshold:
        return names[idx], best
    return None, best
