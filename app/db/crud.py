import json
import numpy as np
from sqlalchemy.orm import Session
from app.db.models import Student, StudentEmbedding, AttendanceSession
from app.db.models import ClassRoom


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

    row = db.query(StudentEmbedding).filter(StudentEmbedding.student_id == student_id).first()
    if row is None:
        row = StudentEmbedding(
            student_id=student_id,
            dim=int(emb.shape[0]),
            vector=vec_bytes,
            source="enroll",
        )
        db.add(row)
    else:
        row.dim = int(emb.shape[0])
        row.vector = vec_bytes
        row.source = "enroll"

    db.commit()
    db.refresh(row)
    return row


def insert_embedding(db: Session, student_id: str, emb: np.ndarray, source: str = "enroll"):
    emb = np.asarray(emb, dtype=np.float32).reshape(-1)
    row = StudentEmbedding(
        student_id=student_id,
        dim=int(emb.shape[0]),
        vector=emb.tobytes(),
        source=source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def load_gallery_for_class(db: Session, class_id: str):
    q = (
        db.query(Student, StudentEmbedding)
        .join(StudentEmbedding, StudentEmbedding.student_id == Student.id)
        .filter(Student.class_id == class_id)
    ).all()

    names, embs = [], []
    for st, eb in q:
        names.append(st.name)
        embs.append(np.frombuffer(eb.vector, dtype=np.float32))

    if not embs:
        return [], np.zeros((0, 0), dtype=np.float32)

    return names, np.stack(embs, axis=0)

def save_attendance_session(db: Session, session_id: str, class_id: str, images_count: int, result: dict, threshold: float = 0.6):
    row = AttendanceSession(
        id=session_id,
        class_id=class_id,
        images_count=images_count,
        threshold=threshold,
        unknown_faces_count=int(result.get("unknown_faces_count", 0)),
        note=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    return row

def list_sessions(db: Session, class_id: str, limit: int = 50):
    return (
        db.query(AttendanceSession)
        .filter(AttendanceSession.class_id == class_id)
        .order_by(AttendanceSession.created_at.desc())
        .limit(limit)
        .all()
    )

def get_session(db: Session, session_id: str):
    return db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()


# danh sách lớp 

def list_classes(db: Session, limit: int = 100):
    return db.query(ClassRoom).order_by(ClassRoom.created_at.desc()).limit(limit).all()

# danh sach student trong class
def list_students_in_class(db: Session, class_id: str, limit: int = 500):
    return (
        db.query(Student)
            .filter(Student.class_id == class_id)
            .order_by(Student.created_at.asc())
            .limit(limit)
            .all()
    ) 

def upsert_class(db: Session, class_id: str, name: str | None = None):
    row = db.query(ClassRoom).filter(ClassRoom.id == class_id).first()
    if row is None:
        row = ClassRoom(id=class_id, name=name)
        db.add(row)
        db.commit()
        db.refresh(row)
    else:
        # nếu muốn cập nhật tên lớp khi có name
        if name is not None:
            row.name = name
            db.commit()
            db.refresh(row)
    return row