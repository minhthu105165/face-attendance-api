from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, LargeBinary
from app.db.database import Base

class ClassRoom(Base):
    __tablename__ = "classes"
    id = Column(String, primary_key=True)  # 10A1
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True)          # HS001
    class_id = Column(String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class StudentEmbedding(Base):
    __tablename__ = "student_embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    dim = Column(Integer, nullable=False)
    vector = Column(LargeBinary, nullable=False)
    source = Column(String, default="enroll")
    created_at = Column(DateTime, default=datetime.utcnow)

# ✅ Alias để code cũ import Embedding vẫn chạy
Embedding = StudentEmbedding

class StudentEnrollImage(Base):
    __tablename__ = "student_enroll_images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(String, primary_key=True)  # uuid
    class_id = Column(String, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    threshold = Column(Float, default=0.6)
    images_count = Column(Integer, default=0)
    unknown_faces_count = Column(Integer, default=0)
    note = Column(Text, nullable=True)

class AttendanceImage(Base):
    __tablename__ = "attendance_images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceFace(Base):
    __tablename__ = "attendance_faces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("attendance_images.id", ondelete="CASCADE"), nullable=False, index=True)

    bbox = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    embedding = Column(LargeBinary, nullable=True)

    matched_student_id = Column(String, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    match_score = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # matched|unknown|maybe
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceResult(Base):
    __tablename__ = "attendance_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False)  # present|absent
    best_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CleanupRun(Base):
    __tablename__ = "cleanup_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ran_at = Column(DateTime, default=datetime.utcnow)
    deleted_sessions = Column(Integer, default=0)
    deleted_files = Column(Integer, default=0)
    note = Column(Text, nullable=True)
