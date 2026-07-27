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
    elapsed_ms,
    mark_error,
    otel_logger
)
from app.observability.prometheus_metrics import (
    cache_operations_total, cache_duration,
    youtube_api_requests_total, youtube_api_duration, youtube_api_failures,
    analytics_duration, llm_requests_total, llm_duration, llm_failures_total,
    database_operations_total, database_duration,
    channel_analyses_total, channel_analysis_duration, response_generation_duration
)
from app.config import settings

router = APIRouter()

class SearchRequest(BaseModel):
    channel: str

@router.post("/analyze")
async def analyze_creator(req: SearchRequest, request: Request, db: Session = Depends(get_db)):
    start_time = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    channel_query = req.channel.strip()
    
    if not channel_query:
        raise HTTPException(status_code=400, detail="Channel query is required")

    # Intentional Chaos Trigger for Live Demos
    if channel_query.lower() == "slow_demo":
        time.sleep(3.5)
    elif channel_query.lower() == "error_demo":
        raise HTTPException(status_code=500, detail="Simulated 500 Internal Server Error for SigNoz Live Demo")

    with tracer.start_as_current_span("creator.analyze") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("channel.query", channel_query)
        span.set_attribute("ai.provider", settings.AI_PROVIDER)

        # 1. Redis Cache Lookup Span
        cache_start = time.perf_counter()
        cached_data = CacheService.get(channel_query)
        cache_duration.labels(operation="get").observe(elapsed_ms(cache_start) / 1000)
        cache_operations_total.labels(operation="get", status="hit" if cached_data else "miss").inc()
        
        if cached_data:
            duration = elapsed_ms(start_time)
            otel_logger.info(f"Successfully processed /analyze via Cache Hit", extra={
                "request_id": request_id,
                "endpoint": "/analyze",
                "channel": channel_query,
                "execution_time_ms": round(duration, 2)
            })
            return cached_data

        # 2. YouTube API Fetch Span
        yt_start = time.perf_counter()
        with tracer.start_as_current_span("youtube.fetch_channel") as yt_span:
            yt_span.set_attribute("channel.query", channel_query)
            try:
                yt = YouTubeService()
                channel_id = yt.resolve_channel_id(channel_query)
                channel_details = yt.get_channel_details(channel_id)
                videos = yt.get_recent_videos(channel_details.get("uploads_playlist_id"), max_results=20)
                youtube_api_requests_total.labels(operation="fetch_channel").inc()
                youtube_api_duration.labels(operation="fetch_channel").observe(elapsed_ms(yt_start) / 1000)
            except ValueError as ve:
                mark_error(yt_span, ve)
                youtube_api_failures.labels(operation="fetch_channel", error_type="value_error").inc()
                raise HTTPException(status_code=404, detail=str(ve))
            except Exception as e:
                mark_error(yt_span, e)
                youtube_api_failures.labels(operation="fetch_channel", error_type="api_error").inc()
                raise HTTPException(status_code=502, detail=f"YouTube API Error: {str(e)}")

        # 3. Analytics Engine Span
        analytics_start = time.perf_counter()
        analytics_results = AnalyticsEngine.analyze(channel_details, videos)
        analytics_duration.observe(elapsed_ms(analytics_start) / 1000)

        # 4. Provider-Agnostic AI Report Generation Span
        llm_start = time.perf_counter()
        with tracer.start_as_current_span("response.generate"):
            ai_provider = AIService.get_provider()
            llm_requests_total.labels(provider=settings.AI_PROVIDER).inc()
            try:
                ai_report = await ai_provider.generate_report(channel_details, analytics_results, videos)
                ai_report_dict = ai_report.model_dump()
                llm_duration.labels(provider=settings.AI_PROVIDER).observe(elapsed_ms(llm_start) / 1000)
            except Exception as e:
                llm_failures_total.labels(provider=settings.AI_PROVIDER, error_type="generation_error").inc()
                raise

        response_payload = {
            "channel": channel_details,
            "videos": videos,
            "analytics": analytics_results,
            "ai_report": ai_report_dict
        }

        # 5. Database Persistence Span & Metric Tracking
        db_start = time.perf_counter()
        with tracer.start_as_current_span("database.persist_analysis") as db_span:
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
                    database_operations_total.labels(operation="create", table="channels").inc()

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
                database_operations_total.labels(operation="create", table="analysis_reports").inc()
                database_duration.labels(operation="persist_analysis", table="analysis_reports").observe(elapsed_ms(db_start) / 1000)
            except Exception as dbe:
                mark_error(db_span, dbe)
                database_operations_total.labels(operation="create", table="analysis_reports", error_type="db_error").inc()
                otel_logger.error(f"Database save error: {dbe}", extra={"error_details": str(dbe)})

        # 6. Store in Redis Cache
        cache_set_start = time.perf_counter()
        CacheService.set(channel_query, response_payload)
        cache_duration.labels(operation="set").observe(elapsed_ms(cache_set_start) / 1000)
        cache_operations_total.labels(operation="set", status="success").inc()
        
        if channel_details.get("custom_url"):
            CacheService.set(channel_details["custom_url"], response_payload)
            cache_operations_total.labels(operation="set", status="success").inc()

        total_duration = elapsed_ms(start_time)
        channel_analyses_total.labels(ai_provider=settings.AI_PROVIDER).inc()
        channel_analysis_duration.labels(ai_provider=settings.AI_PROVIDER).observe(total_duration / 1000)
        response_generation_duration.labels(response_type="creator_analysis").observe(total_duration / 1000)
        
        otel_logger.info(f"Successfully processed /analyze via API & AI Execution", extra={
            "request_id": request_id,
            "endpoint": "/analyze",
            "channel": channel_query,
            "provider": settings.AI_PROVIDER,
            "execution_time_ms": round(total_duration, 2)
        })

        return response_payload
