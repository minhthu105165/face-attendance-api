from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True, index=True)          # student_id
    class_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    embedding = relationship("Embedding", back_populates="student", uselist=False, cascade="all, delete-orphan")

class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), unique=True, index=True, nullable=False)
    dim = Column(Integer, nullable=False)
    vector = Column(LargeBinary, nullable=False)               # store float32 bytes
    updated_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="embedding")

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(String, primary_key=True, index=True)          # session_id (uuid)
    class_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    images_count = Column(Integer, default=0)
    result_json = Column(Text, nullable=False)                 # store JSON string
