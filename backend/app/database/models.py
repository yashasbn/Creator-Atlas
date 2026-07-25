import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text, BigInteger
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ChannelModel(Base):
    __tablename__ = "channels"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(String, unique=True, index=True, nullable=False)
    custom_url = Column(String, index=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    subscriber_count = Column(BigInteger, default=0)
    view_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    country = Column(String, nullable=True)
    published_at = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reports = relationship("AnalysisReportModel", back_populates="channel", cascade="all, delete-orphan")


class AnalysisReportModel(Base):
    __tablename__ = "analysis_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_db_id = Column(String, ForeignKey("channels.id"), nullable=False)
    
    analytics_summary = Column(JSON, nullable=False)
    recent_videos = Column(JSON, nullable=False)
    
    ai_provider = Column(String, nullable=False)
    executive_summary = Column(Text, nullable=False)
    primary_topics = Column(JSON, nullable=False)
    target_audience = Column(Text, nullable=False)
    content_style = Column(JSON, nullable=False)
    upload_consistency = Column(Text, nullable=False)
    engagement_analysis = Column(Text, nullable=False)
    creator_strengths = Column(JSON, nullable=False)
    improvement_opportunities = Column(JSON, nullable=False)
    
    rating_content_quality = Column(Float, nullable=False)
    rating_consistency = Column(Float, nullable=False)
    rating_engagement = Column(Float, nullable=False)
    rating_branding = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    channel = relationship("ChannelModel", back_populates="reports")
