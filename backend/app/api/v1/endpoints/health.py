from fastapi import APIRouter
from app.config import settings
from app.services.cache_service import CacheService

router = APIRouter()

@router.get("/health")
def health_check():
    cache_stats = CacheService.get_stats()
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "ai_provider": settings.AI_PROVIDER,
        "cache": cache_stats
    }
