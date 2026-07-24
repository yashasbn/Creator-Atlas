from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.youtube_service import YouTubeService
from app.services.analytics_service import AnalyticsEngine
from app.services.ai.service import AIService
from app.services.cache_service import CacheService
from app.database.session import get_db
from app.database.models import ChannelModel, AnalysisReportModel
from app.observability.tracer import tracer
from app.config import settings

router = APIRouter()

class SearchRequest(BaseModel):
    channel: str

@router.post("/analyze")
async def analyze_creator(req: SearchRequest, db: Session = Depends(get_db)):
    channel_query = req.channel.strip()
    if not channel_query:
        raise HTTPException(status_code=400, detail="Channel query is required")

    with tracer.start_as_current_span("analyze_endpoint") as span:
        span.set_attribute("channel.query", channel_query)

        # 1. Redis / Memory Cache Lookup
        with tracer.start_as_current_span("redis_cache_lookup"):
            cached_data = CacheService.get(channel_query)
            if cached_data:
                span.set_attribute("cache.hit", True)
                return cached_data
            span.set_attribute("cache.hit", False)

        # 2. YouTube API Fetch
        with tracer.start_as_current_span("youtube_api_fetch"):
            try:
                yt = YouTubeService()
                channel_id = yt.resolve_channel_id(channel_query)
                channel_details = yt.get_channel_details(channel_id)
                videos = yt.get_recent_videos(channel_details.get("uploads_playlist_id"), max_results=20)
            except ValueError as ve:
                raise HTTPException(status_code=404, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"YouTube API Error: {str(e)}")

        # 3. Analytics Engine
        with tracer.start_as_current_span("analytics_engine_compute"):
            analytics_results = AnalyticsEngine.analyze(channel_details, videos)

        # 4. Provider-Agnostic AI Report Generation
        with tracer.start_as_current_span("ai_llm_generation") as ai_span:
            ai_span.set_attribute("ai.provider", settings.AI_PROVIDER)
            ai_provider = AIService.get_provider()
            ai_report = await ai_provider.generate_report(channel_details, analytics_results, videos)
            ai_report_dict = ai_report.model_dump()

        response_payload = {
            "channel": channel_details,
            "videos": videos,
            "analytics": analytics_results,
            "ai_report": ai_report_dict
        }

        # 5. Save to Database & Cache
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
            print(f"Database save error: {dbe}")

        # Store in Redis / Cache for 24h
        CacheService.set(channel_query, response_payload)
        if channel_details.get("custom_url"):
            CacheService.set(channel_details["custom_url"], response_payload)

        return response_payload
