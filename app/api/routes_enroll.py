from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import numpy as np

from app.deps import get_db
from app.core.uniface_engine import UniFaceEngine
from app.db.crud import upsert_class, upsert_student, upsert_embedding
from app.utils.image import decode_upload_to_bgr

router = APIRouter(prefix="/enroll", tags=["enroll"])
engine = UniFaceEngine()

@router.post("/")
async def enroll(
    class_id: str = Form(...),
    student_id: str = Form(...),
    student_name: str = Form(...),
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if len(images) == 0:
        raise HTTPException(400, "No images")

    embs = []
    for f in images:
        data = await f.read()
        img = decode_upload_to_bgr(data)
        if img is None:
            continue

        faces = engine.detect(img)
        if not faces:
            continue

        faces = sorted(faces, key=lambda x: x.confidence, reverse=True)
        face = faces[0]
        emb = engine.embedding(img, face.landmarks)
        embs.append(emb)

    if len(embs) == 0:
        raise HTTPException(400, "No valid face found in uploaded images")

    mean_emb = np.mean(np.stack(embs, axis=0), axis=0)
    mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-9)

    upsert_class(db, class_id=class_id, name=class_id) # Ensure class exists
    upsert_student(db, student_id=student_id, class_id=class_id, name=student_name)
    upsert_embedding(db, student_id=student_id, emb=mean_emb)

    return {"ok": True, "student_id": student_id, "student_name": student_name, "images_used": len(embs)}
