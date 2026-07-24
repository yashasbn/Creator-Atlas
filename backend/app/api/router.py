from fastapi import APIRouter
from app.api.v1.endpoints import analyze, health, metrics

api_router = APIRouter()
api_router.include_router(analyze.router, tags=["analyze"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, tags=["metrics"])
