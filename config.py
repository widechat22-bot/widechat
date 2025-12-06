import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Firebase
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "")
    
    # Google Drive
    GOOGLE_DRIVE_CREDENTIALS: str = os.getenv("GOOGLE_DRIVE_CREDENTIALS", "")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    class Config:
        env_file = ".env"

settings = Settings()