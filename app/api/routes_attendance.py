from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid

from app.deps import get_db
from app.core.uniface_engine import UniFaceEngine
from app.core.matching import best_match
from app.db.crud import load_gallery_for_class, save_attendance_session
from app.utils.image import decode_upload_to_bgr

router = APIRouter(prefix="/attendance", tags=["attendance"])
engine = UniFaceEngine()

@router.post("/")
async def attendance(
    class_id: str = Form(...),
    images: list[UploadFile] = File(...),
    threshold: float = Form(0.60),
    db: Session = Depends(get_db),
):
    names, gallery_embs = load_gallery_for_class(db, class_id)
    if len(names) == 0:
        raise HTTPException(400, f"No gallery embeddings for class_id={class_id}. Enroll students first.")

    present_best = {}  # name -> best_score
    unknown_faces = 0

    for f in images:
        data = await f.read()
        img = decode_upload_to_bgr(data)
        if img is None:
            continue

        faces = engine.detect(img)
        for face in faces:
            emb = engine.embedding(img, face.landmarks)
            matched, score = best_match(emb, names, gallery_embs, threshold=threshold)
            if matched is None:
                unknown_faces += 1
            else:
                prev = present_best.get(matched, 0.0)
                if score > prev:
                    present_best[matched] = score

    present = sorted(present_best.keys())
    absent = sorted(list(set(names) - set(present)))

    result = {
        "class_id": class_id,
        "count_total": len(names),
        "count_present": len(present),
        "present": [{"name": n, "score": present_best[n]} for n in present],
        "absent": absent,
        "unknown_faces_count": unknown_faces,
        "threshold": threshold,
    }

    session_id = str(uuid.uuid4())
    save_attendance_session(db, session_id=session_id, class_id=class_id, images_count=len(images), result=result)

    result["session_id"] = session_id
    return result
