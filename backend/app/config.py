from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "BlueGuard"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    NODE_ENV: str = "development"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # Database (Supabase PostgreSQL)
    DATABASE_URL: str = ""
    
    # Security & Authentication
    SECRET_KEY: str = "change-this-in-production"
    JWT_SECRET: str = "change-this-in-production"
    JWT_EXPIRES_IN: str = "7d"
    
    # Google Gemini
    GEMINI_API_KEY: str = ""
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Model paths (local fallback)
    YOLO_MODEL_PATH: str = "models/pollution_yolo.pt"
    LSTM_MODEL_PATH: str = "models/route_lstm.pt"
    
    # Model Registry Configuration
    # Storage backend: "local", "supabase", "s3", "http"
    MODEL_STORAGE_BACKEND: str = "local"
    MODEL_CACHE_DIR: Optional[str] = None  # Defaults to ~/.blueguard/models
    
    # AWS S3 Configuration (for model storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_MODEL_BUCKET: Optional[str] = None
    
    # Supabase Storage Configuration (for models)
    SUPABASE_MODEL_BUCKET: str = "models"
    
    # Model versions (semantic versioning)
    YOLO_MODEL_VERSION: str = "1.0.0"
    LSTM_MODEL_VERSION: str = "1.0.0"
    
    # Remote model paths (used when MODEL_STORAGE_BACKEND != "local")
    # Format depends on backend:
    #   - S3: "bucket-name/path/to/model.pt"
    #   - Supabase: "bucket-name/path/to/model.pt"
    #   - HTTP: "https://example.com/models/model.pt"
    YOLO_MODEL_REMOTE_PATH: Optional[str] = None
    LSTM_MODEL_REMOTE_PATH: Optional[str] = None
    
    # Thresholds
    POLLUTION_CONFIDENCE_THRESHOLD: float = 0.5
    IUU_RISK_THRESHOLD: float = 0.7
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    # Optional: Redis (only if using Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
