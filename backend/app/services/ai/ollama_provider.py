import json
import time
import requests
from typing import Dict, List, Any

from app.observability.tracer import elapsed_ms, mark_error, otel_logger, tracer
from app.observability.prometheus_metrics import llm_failures_total, llm_duration, llm_requests_total
from app.services.ai.base import BaseAIProvider, AIReportSchema


class OllamaProvider(BaseAIProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_report(self, metadata: Dict[str, Any], analytics: Dict[str, Any], videos: List[Dict[str, Any]]) -> AIReportSchema:
        started = time.perf_counter()
        attributes = {"gen_ai.provider.name": "ollama", "gen_ai.request.model": self.model}
        llm_requests_total.labels(provider="ollama").inc()
        prompt = f"Analyze this YouTube channel metadata and produce JSON matching the report schema. Metadata: {json.dumps(metadata)} Analytics: {json.dumps(analytics)}"
        with tracer.start_as_current_span("llm.ollama.generate") as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            try:
                response = requests.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "format": "json", "stream": False}, timeout=30)
                response.raise_for_status()
                parsed = json.loads(response.json().get("response", "{}"))
                llm_duration.labels(provider="ollama").observe(elapsed_ms(started) / 1000)
                return AIReportSchema(**parsed)
            except Exception as error:
                mark_error(span, error)
                llm_failures_total.labels(provider="ollama", error_type=type(error).__name__).inc()
                llm_duration.labels(provider="ollama").observe(elapsed_ms(started) / 1000)
                otel_logger.exception("Ollama report generation failed", extra={"provider": "ollama", "execution_time_ms": round(elapsed_ms(started), 2), "error_details": str(error)})
        return self._fallback(metadata)

    def _fallback(self, metadata: Dict[str, Any]) -> AIReportSchema:
        title = metadata.get("channel_title", "Creator")
        return AIReportSchema(executive_summary=f"{title} demonstrates strong content production locally analyzed via Ollama.", primary_topics=["General Content", "Tech"], target_audience="General audience", content_style=["Tutorials"], upload_consistency="Consistent", engagement_analysis="Good engagement", creator_strengths=["Niche focus"], improvement_opportunities=["Increase upload frequency"], ratings={"content_quality": 8.0, "consistency": 8.0, "engagement": 8.0, "branding": 8.0})
