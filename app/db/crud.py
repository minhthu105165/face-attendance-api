import json
import numpy as np
from sqlalchemy.orm import Session
from app.db.models import Student, Embedding, AttendanceSession
from datetime import datetime

def upsert_student(db: Session, student_id: str, class_id: str, name: str):
    st = db.query(Student).filter(Student.id == student_id).first()
    if st is None:
        st = Student(id=student_id, class_id=class_id, name=name)
        db.add(st)
    else:
        st.class_id = class_id
        st.name = name
    db.commit()
    db.refresh(st)
    return st

def upsert_embedding(db: Session, student_id: str, emb: np.ndarray):
    emb = np.asarray(emb, dtype=np.float32).reshape(-1)
    vec_bytes = emb.tobytes()

    row = db.query(Embedding).filter(Embedding.student_id == student_id).first()
    if row is None:
        row = Embedding(student_id=student_id, dim=int(emb.shape[0]), vector=vec_bytes, updated_at=datetime.utcnow())
        db.add(row)
    else:
        row.dim = int(emb.shape[0])
        row.vector = vec_bytes
        row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row

def load_gallery_for_class(db: Session, class_id: str):
    # returns (names, embs[N,D])
    q = (
        db.query(Student, Embedding)
        .join(Embedding, Embedding.student_id == Student.id)
        .filter(Student.class_id == class_id)
    ).all()

    names = []
    embs = []
    for st, eb in q:
        v = np.frombuffer(eb.vector, dtype=np.float32)
        names.append(st.name)
        embs.append(v)

    if not embs:
        return [], np.zeros((0, 0), dtype=np.float32)

    embs = np.stack(embs, axis=0)
    return names, embs

def save_attendance_session(db: Session, session_id: str, class_id: str, images_count: int, result: dict):
    row = AttendanceSession(
        id=session_id,
        class_id=class_id,
        images_count=images_count,
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    return row
