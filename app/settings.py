from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "face-attendance"
    db_url: str = "sqlite:///./face_attendance.db"
    storage_dir: str = "./storage"
    retention_days: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
