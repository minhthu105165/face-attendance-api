from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.deps import get_db
from app.db.crud import list_students_in_class

router = APIRouter(prefix="/students", tags=["students"])

@router.get("")
def get_students(class_id: str = Query(...), db: Session = Depends(get_db)):
    rows = list_students_in_class(db, class_id=class_id)
    return [
        {"student_id": r.id, "name": r.name, "class_id": r.class_id, "created_at": r.created_at}
        for r in rows
    ]
