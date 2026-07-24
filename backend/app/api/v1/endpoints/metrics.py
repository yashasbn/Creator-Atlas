from fastapi import APIRouter
from app.observability.metrics import get_metrics_data
from app.services.cache_service import CacheService

router = APIRouter()

@router.get("/metrics")
def get_metrics():
    return {
        "telemetry": get_metrics_data(),
        "cache": CacheService.get_stats()
    }
