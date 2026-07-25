from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Creator Atlas"
    API_V1_STR: str = "/api/v1"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    YOUTUBE_API_KEY: str = ""
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 86400
    DATABASE_URL: str = "sqlite:///./creator_atlas.db"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "localhost:4317"
    OTEL_EXPORTER_OTLP_INSECURE: bool = True
    OTEL_SERVICE_NAME: str = "creator-atlas-backend"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
