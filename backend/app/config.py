from pydantic_settings import BaseSettings
from functools import lru_cache

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
    
    # Model paths
    YOLO_MODEL_PATH: str = "models/pollution_yolo.pt"
    LSTM_MODEL_PATH: str = "models/route_lstm.pt"
    
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
