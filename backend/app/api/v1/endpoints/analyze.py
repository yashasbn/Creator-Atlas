import uuid
import time
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.youtube_service import YouTubeService
from app.services.analytics_service import AnalyticsEngine
from app.services.ai.service import AIService
from app.services.cache_service import CacheService
from app.database.session import get_db
from app.database.models import ChannelModel, AnalysisReportModel
from app.observability.tracer import (
    tracer, 
    http_requests_total, 
    http_request_duration_seconds, 
    db_query_duration, 
    otel_logger
)
from app.config import settings

router = APIRouter()

class SearchRequest(BaseModel):
    channel: str

@router.post("/analyze")
async def analyze_creator(req: SearchRequest, request: Request, db: Session = Depends(get_db)):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    channel_query = req.channel.strip()
    
    http_requests_total.add(1, {"endpoint": "/analyze"})

    if not channel_query:
        raise HTTPException(status_code=400, detail="Channel query is required")

    # Intentional Chaos Trigger for Live Demos
    if channel_query.lower() == "slow_demo":
        time.sleep(3.5)
    elif channel_query.lower() == "error_demo":
        raise HTTPException(status_code=500, detail="Simulated 500 Internal Server Error for SigNoz Live Demo")

    with tracer.start_as_current_span("POST /analyze") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/analyze")
        span.set_attribute("request_id", request_id)
        span.set_attribute("channel.query", channel_query)
        span.set_attribute("ai.provider", settings.AI_PROVIDER)

        # 1. Redis Cache Lookup Span
        cached_data = CacheService.get(channel_query)
        if cached_data:
            duration = time.time() - start_time
            http_request_duration_seconds.record(duration, {"endpoint": "/analyze", "cache": "hit"})
            otel_logger.info(f"Successfully processed /analyze via Cache Hit", extra={
                "request_id": request_id,
                "endpoint": "/analyze",
                "channel": channel_query,
                "execution_time": duration
            })
            return cached_data

        # 2. YouTube API Fetch Span
        with tracer.start_as_current_span("youtube_api_fetch") as yt_span:
            yt_span.set_attribute("channel.query", channel_query)
            try:
                yt = YouTubeService()
                channel_id = yt.resolve_channel_id(channel_query)
                channel_details = yt.get_channel_details(channel_id)
                videos = yt.get_recent_videos(channel_details.get("uploads_playlist_id"), max_results=20)
            except ValueError as ve:
                yt_span.record_exception(ve)
                raise HTTPException(status_code=404, detail=str(ve))
            except Exception as e:
                yt_span.record_exception(e)
                raise HTTPException(status_code=502, detail=f"YouTube API Error: {str(e)}")

        # 3. Analytics Engine Span
        with tracer.start_as_current_span("analytics_engine_compute"):
            analytics_results = AnalyticsEngine.analyze(channel_details, videos)

        # 4. Provider-Agnostic AI Report Generation Span
        with tracer.start_as_current_span("ai_llm_generation"):
            ai_provider = AIService.get_provider()
            ai_report = await ai_provider.generate_report(channel_details, analytics_results, videos)
            ai_report_dict = ai_report.model_dump()

        response_payload = {
            "channel": channel_details,
            "videos": videos,
            "analytics": analytics_results,
            "ai_report": ai_report_dict
        }

        # 5. Database Persistence Span & Metric Tracking
        db_start = time.time()
        with tracer.start_as_current_span("postgresql_database_store") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            try:
                db_channel = db.query(ChannelModel).filter_by(channel_id=channel_id).first()
                if not db_channel:
                    db_channel = ChannelModel(
                        channel_id=channel_id,
                        custom_url=channel_details.get("custom_url"),
                        title=channel_details.get("channel_title"),
                        description=channel_details.get("description"),
                        subscriber_count=channel_details.get("subscriber_count", 0),
                        view_count=channel_details.get("view_count", 0),
                        video_count=channel_details.get("video_count", 0),
                        country=channel_details.get("country"),
                        published_at=channel_details.get("published_at")
                    )
                    db.add(db_channel)
                    db.commit()
                    db.refresh(db_channel)

                db_report = AnalysisReportModel(
                    channel_db_id=db_channel.id,
                    analytics_summary=analytics_results,
                    recent_videos=videos,
                    ai_provider=settings.AI_PROVIDER,
                    executive_summary=ai_report_dict["executive_summary"],
                    primary_topics=ai_report_dict["primary_topics"],
                    target_audience=ai_report_dict["target_audience"],
                    content_style=ai_report_dict["content_style"],
                    upload_consistency=ai_report_dict["upload_consistency"],
                    engagement_analysis=ai_report_dict["engagement_analysis"],
                    creator_strengths=ai_report_dict["creator_strengths"],
                    improvement_opportunities=ai_report_dict["improvement_opportunities"],
                    rating_content_quality=ai_report_dict["ratings"].get("content_quality", 8.0),
                    rating_consistency=ai_report_dict["ratings"].get("consistency", 8.0),
                    rating_engagement=ai_report_dict["ratings"].get("engagement", 8.0),
                    rating_branding=ai_report_dict["ratings"].get("branding", 8.0)
                )
                db.add(db_report)
                db.commit()
            except Exception as dbe:
                db_span.record_exception(dbe)
                otel_logger.error(f"Database save error: {dbe}", extra={"error_details": str(dbe)})

        db_duration = time.time() - db_start
        db_query_duration.record(db_duration, {"db.system": "postgresql"})

        # 6. Store in Redis Cache
        CacheService.set(channel_query, response_payload)
        if channel_details.get("custom_url"):
            CacheService.set(channel_details["custom_url"], response_payload)

        total_duration = time.time() - start_time
        http_request_duration_seconds.record(total_duration, {"endpoint": "/analyze", "cache": "miss"})
        
        otel_logger.info(f"Successfully processed /analyze via API & AI Execution", extra={
            "request_id": request_id,
            "endpoint": "/analyze",
            "channel": channel_query,
            "provider": settings.AI_PROVIDER,
            "execution_time": total_duration
        })

        return response_payload
