"""Prometheus metrics for Creator Atlas.

This module defines and initializes Prometheus metrics for the application.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import start_http_server

# HTTP metrics
http_requests_total = Counter(
    'creator_atlas_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'creator_atlas_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_errors_total = Counter(
    'creator_atlas_http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'error_type']
)

# Cache metrics
cache_operations_total = Counter(
    'creator_atlas_cache_operations_total',
    'Total cache operations',
    ['operation', 'status']
)

cache_duration = Histogram(
    'creator_atlas_cache_duration_seconds',
    'Cache operation duration in seconds',
    ['operation']
)

cache_size = Gauge(
    'creator_atlas_cache_size',
    'Current cache size'
)

# YouTube API metrics
youtube_api_requests_total = Counter(
    'creator_atlas_youtube_api_requests_total',
    'Total YouTube API requests',
    ['operation']
)

youtube_api_duration = Histogram(
    'creator_atlas_youtube_api_duration_seconds',
    'YouTube API request duration in seconds',
    ['operation']
)

youtube_api_failures = Counter(
    'creator_atlas_youtube_api_failures_total',
    'Total YouTube API failures',
    ['operation', 'error_type']
)

# AI/LLM metrics
llm_requests_total = Counter(
    'creator_atlas_llm_requests_total',
    'Total LLM requests',
    ['provider']
)

llm_duration = Histogram(
    'creator_atlas_llm_duration_seconds',
    'LLM request duration in seconds',
    ['provider']
)

llm_failures_total = Counter(
    'creator_atlas_llm_failures_total',
    'Total LLM failures',
    ['provider', 'error_type']
)

# Analytics metrics
analytics_duration = Histogram(
    'creator_atlas_analytics_duration_seconds',
    'Analytics processing duration in seconds'
)

# Database metrics
database_operations_total = Counter(
    'creator_atlas_database_operations_total',
    'Total database operations',
    ['operation', 'table']
)

database_duration = Histogram(
    'creator_atlas_database_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table']
)

# Application info
app_info = Info(
    'creator_atlas_info',
    'Application information'
)

# Channel analysis metrics
channel_analyses_total = Counter(
    'creator_atlas_channel_analyses_total',
    'Total channel analyses performed',
    ['ai_provider']
)

channel_analysis_duration = Histogram(
    'creator_atlas_channel_analysis_duration_seconds',
    'Channel analysis duration in seconds',
    ['ai_provider']
)

# Response generation metrics
response_generation_duration = Histogram(
    'creator_atlas_response_generation_duration_seconds',
    'Response generation duration in seconds',
    ['response_type']
)


def start_metrics_server(port: int = 9090):
    """Start the Prometheus metrics server."""
    start_http_server(port)
    print(f"Prometheus metrics server started on port {port}")


def init_app_info():
    """Initialize application info metrics."""
    from app.config import settings
    app_info.info({
        'name': settings.PROJECT_NAME,
        'version': settings.SERVICE_VERSION,
        'environment': settings.ENVIRONMENT
    })
