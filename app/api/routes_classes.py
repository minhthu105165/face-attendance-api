from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db.models import ClassRoom  # hoặc import crud.list_classes nếu bạn đã tách crud

router = APIRouter(prefix="/classes", tags=["classes"])

@router.get("")
def get_classes(db: Session = Depends(get_db)):
    rows = db.query(ClassRoom).order_by(ClassRoom.created_at.desc()).all()
    return [
        {
            "class_id": r.id,
            "name": r.name,
            "created_at": r.created_at,
        }
        for r in rows
    ]
