import uuid
import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.core.uniface_engine import UniFaceEngine
from app.db.crud import load_gallery_for_class, save_attendance_session, list_sessions, get_session
from app.utils.image import decode_upload_to_bgr

from app.core.quality import quality_gate
from app.core.matching import best_match
from app.core.attendance_logic import update_present_best, build_result



router = APIRouter(prefix="/attendance", tags=["attendance"])
engine = UniFaceEngine()


@router.post("/")
async def attendance(
    class_id: str = Form(...),
    images: list[UploadFile] = File(...),
    threshold: float = Form(0.60),
    db: Session = Depends(get_db),
):
    # gallery: names lặp theo số embedding (vì enroll bạn đã lưu nhiều embeddings/1 student)
    names, gallery_embs = load_gallery_for_class(db, class_id)
    if len(names) == 0:
        raise HTTPException(400, f"No gallery embeddings for class_id={class_id}. Enroll students first.")

    # danh sách học sinh (unique) để tính absent/present
    all_students = sorted(list(set(names)))

    # quality thresholds (tune)
    min_conf = 0.6
    min_face = 40
    min_blur = 45.0

    dbg = {
        "images_received": len(images),
        "images_decoded": 0,
        "faces_detected": 0,
        "faces_pass_quality": 0,
        "filtered_lowconf": 0,
        "filtered_small": 0,
        "filtered_blur": 0,
        "filtered_empty_crop": 0,
        "gallery_vectors": len(names),
        "gallery_people": len(all_students),
        "quality_thresholds": {"min_conf": min_conf, "min_face": min_face, "min_blur": min_blur},
    }

    present_best = {}
    unknown_faces = 0

    for f in images:
        data = await f.read()
        img = decode_upload_to_bgr(data)
        if img is None:
            continue
        dbg["images_decoded"] += 1

        faces = engine.detect(img)  # multi-face detection
        dbg["faces_detected"] += len(faces)

        for face in faces:
            ok, meta = quality_gate(img, face, min_conf=min_conf, min_face=min_face, min_blur=min_blur)
            if not ok:
                r = meta.get("reason")
                if r == "lowconf":
                    dbg["filtered_lowconf"] += 1
                elif r == "small":
                    dbg["filtered_small"] += 1
                elif r == "blur":
                    dbg["filtered_blur"] += 1
                elif r == "empty_crop":
                    dbg["filtered_empty_crop"] += 1
                continue

            dbg["faces_pass_quality"] += 1

            emb = engine.embedding(img, face.landmarks)
            matched, score = best_match(emb, names, gallery_embs, threshold=threshold)

            if matched is None:
                unknown_faces += 1
            else:
                update_present_best(present_best, matched, score)

    result = build_result(
        class_id=class_id,
        all_names=all_students,
        present_best=present_best,
        unknown_faces=unknown_faces,
        threshold=threshold,
        dbg=dbg,
    )

    session_id = str(uuid.uuid4())
    save_attendance_session(
        db,
        session_id=session_id,
        class_id=class_id,
        images_count=len(images),
        result=result,
        threshold=threshold,
    )

    result["session_id"] = session_id
    return result


@router.get("/sessions")
def get_sessions(class_id: str = Query(...), db: Session = Depends(get_db)):
    rows = list_sessions(db, class_id=class_id)

    now = datetime.now(timezone.utc)
    out = []

    for r in rows:
        created_at = r.created_at
        # SQLite thường trả datetime "naive" (không tz), gắn UTC cho nhất quán
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        expires_at = created_at + timedelta(days=30)
        days_left = (expires_at - now).days
        if days_left < 0:
            days_left = 0

        out.append({
            "session_id": r.id,
            "class_id": r.class_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "days_left": days_left,
            "images_count": r.images_count,
            "unknown_faces_count": r.unknown_faces_count,
            "threshold": r.threshold,
        })

    return out



@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="session not found")

    now = datetime.now(timezone.utc)

    created_at = row.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    expires_at = created_at + timedelta(days=30)
    days_left = (expires_at - now).days
    if days_left < 0:
        days_left = 0

    # parse result json stored in note (nếu note là json)
    result = None
    if row.note:
        try:
            result = json.loads(row.note)
        except Exception:
            result = {"raw_note": row.note}

    return {
        "session_id": row.id,
        "class_id": row.class_id,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "days_left": days_left,
        "images_count": row.images_count,
        "unknown_faces_count": row.unknown_faces_count,
        "threshold": row.threshold,
        "result": result,
    }
