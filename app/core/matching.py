import numpy as np

def best_match(emb: np.ndarray, names: list[str], embs: np.ndarray, threshold: float = 0.60):
    if embs.size == 0:
        return None, 0.0

    emb = np.asarray(emb, dtype=np.float32).reshape(1, -1)
    # assume embeddings are normalized -> dot = cosine
    scores = (embs @ emb.T).reshape(-1)
    idx = int(np.argmax(scores))
    score = float(scores[idx])
    if score >= threshold:
        return names[idx], score
    return None, score
