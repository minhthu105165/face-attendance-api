import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Serve static UI
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/ui", include_in_schema=False)
    def ui():
        return FileResponse(os.path.join(_static_dir, "index.html"))

@app.get("/")
def health():
    return {"service": settings.app_name, "status": "running"}
