from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class AIReportSchema(BaseModel):
    executive_summary: str
    primary_topics: List[str]
    target_audience: str
    content_style: List[str]
    upload_consistency: str
    engagement_analysis: str
    creator_strengths: List[str]
    improvement_opportunities: List[str]
    ratings: Dict[str, float]  # content_quality, consistency, engagement, branding out of 10

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_report(self, metadata: Dict[str, Any], analytics: Dict[str, Any], videos: List[Dict[str, Any]]) -> AIReportSchema:
        pass
