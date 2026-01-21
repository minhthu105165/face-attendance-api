import numpy as np
from uniface import RetinaFace, ArcFace

class UniFaceEngine:
    def __init__(self):
        self.detector = RetinaFace()
        self.recognizer = ArcFace()

    def detect(self, image_bgr):
        return self.detector.detect(image_bgr)

    def embedding(self, image_bgr, landmarks):
        emb = self.recognizer.get_normalized_embedding(image_bgr, landmarks)
        return np.asarray(emb, dtype=np.float32).reshape(-1)
