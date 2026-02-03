from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import uuid
import json


from app.deps import get_db
from app.core.uniface_engine import UniFaceEngine
from app.core.matching import best_match
from app.db.crud import list_sessions, get_session, load_gallery_for_class, save_attendance_session
from app.utils.image import decode_upload_to_bgr
from datetime import datetime, timedelta, timezone
from app.core.quality import blur_score, clamp_bbox_xyxy



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

    # ✅ đặt ngưỡng 1 lần
    min_conf = 0.6
    min_face = 60
    min_blur = 80.0

    # ✅ debug cộng dồn cho cả request (tất cả ảnh)
    dbg = {
        "faces_detected": 0,
        "filtered_lowconf": 0,
        "filtered_small": 0,
        "filtered_blur": 0,
        "filtered_empty_crop": 0,
        "images_received": len(images),
        "images_decoded": 0,
    }

    present_best = {}
    unknown_faces = 0

    for f in images:
        data = await f.read()
        img = decode_upload_to_bgr(data)
        if img is None:
            continue

        dbg["images_decoded"] += 1

        faces = engine.detect(img)

        for face in faces:
            dbg["faces_detected"] += 1

            conf = getattr(face, "confidence", None)
            if conf is not None and conf < min_conf:
                dbg["filtered_lowconf"] += 1
                continue
            
            b = getattr(face, "bbox_xyxy", None)
            if b is None:
                b = getattr(face, "bbox", None)

            if b is None:
                emb = engine.embedding(img, face.landmarks)
            else:
                x1, y1, x2, y2 = b
                H, W = img.shape[:2]
                x1, y1, x2, y2 = clamp_bbox_xyxy(x1, y1, x2, y2, W, H)

                w = x2 - x1
                h = y2 - y1
                if w < min_face or h < min_face:
                    dbg["filtered_small"] += 1
                    continue

                face_crop = img[y1:y2, x1:x2]
                if face_crop.size == 0:
                    dbg["filtered_empty_crop"] += 1
                    continue

                if blur_score(face_crop) < min_blur:
                    dbg["filtered_blur"] += 1
                    continue

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
        "debug": dbg,
        "quality_thresholds": {"min_conf": min_conf, "min_face": min_face, "min_blur": min_blur},
    }

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
