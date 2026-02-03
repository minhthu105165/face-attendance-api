from fastapi import FastAPI
from app.settings import settings
from app.api.routes_enroll import router as enroll_router
from app.api.routes_attendance import router as attendance_router
from app.db.database import Base, engine
from app.api.routes_students import router as students_router
from app.api.routes_classes import router as classes_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.include_router(enroll_router)
app.include_router(attendance_router)
app.include_router(students_router)
app.include_router(classes_router)

@app.get("/")
def health():
    return {"service": settings.app_name, "status": "running"}
