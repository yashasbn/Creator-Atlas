import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Creator Atlas"
    API_V1_STR: str = "/api/v1"
    
    # YouTube API
    YOUTUBE_API_KEY: str = ""
    
    # AI Provider: 'gemini' or 'ollama'
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 86400  # 24 hours
    
    # PostgreSQL
    DATABASE_URL: str = "sqlite:///./creator_atlas.db"  # Fallback SQLite or Postgres URL
    
    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "creator-atlas-backend"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
