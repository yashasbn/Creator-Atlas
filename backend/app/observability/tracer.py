import logging
import json
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from app.config import settings

# 1. Resource & Provider Setup
resource = Resource.create({
    "service.name": settings.OTEL_SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": os.environ.get("ENVIRONMENT", "production")
})

# Tracer Provider Setup
tracer_provider = TracerProvider(resource=resource)
try:
    otlp_trace_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
except Exception as e:
    print(f"OTLP Trace Exporter warning: {e}")

trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("creator-atlas", "1.0.0")

# Meter Provider Setup
try:
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True))
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
except Exception as e:
    print(f"OTLP Metric Exporter warning: {e}")

meter = metrics.get_meter("creator-atlas-meter", "1.0.0")

# 2. Instruments & Metrics Specifications
http_requests_total = meter.create_counter("http_requests_total", description="Total HTTP requests processed")
http_request_duration_seconds = meter.create_histogram("http_request_duration_seconds", unit="s", description="HTTP request latency histogram (P50, P95, P99)")

cache_hits_counter = meter.create_counter("cache_hits_total", description="Total Redis cache hits")
cache_misses_counter = meter.create_counter("cache_misses_total", description="Total Redis cache misses")
cache_latency_histogram = meter.create_histogram("cache_latency_seconds", unit="s", description="Redis cache operation duration")

youtube_api_failures = meter.create_counter("youtube_api_failures_total", description="Total YouTube API request failures")
youtube_api_duration = meter.create_histogram("youtube_api_duration_seconds", unit="s", description="YouTube API call duration")

db_query_duration = meter.create_histogram("db_query_duration_seconds", unit="s", description="Database query execution duration")

llm_requests_total = meter.create_counter("llm_requests_total", description="Total LLM generation requests")
llm_failures_total = meter.create_counter("llm_failures_total", description="Total LLM generation failures")
llm_latency_histogram = meter.create_histogram("llm_latency_seconds", unit="s", description="LLM inference latency")

# 3. Correlation Log Formatter for OpenTelemetry Context
class OTELJsonFormatter(logging.Formatter):
    def format(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        log_payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "trace_id": f"{ctx.trace_id:032x}" if ctx.is_valid else "0"*32,
            "span_id": f"{ctx.span_id:016x}" if ctx.is_valid else "0"*16,
            "service": settings.OTEL_SERVICE_NAME,
        }
        if hasattr(record, "request_id"):
            log_payload["request_id"] = record.request_id
        if hasattr(record, "endpoint"):
            log_payload["endpoint"] = record.endpoint
        if hasattr(record, "channel"):
            log_payload["channel"] = record.channel
        if hasattr(record, "provider"):
            log_payload["provider"] = record.provider
        if hasattr(record, "execution_time"):
            log_payload["execution_time"] = record.execution_time
        if hasattr(record, "error_details"):
            log_payload["error_details"] = record.error_details

        return json.dumps(log_payload)

def get_otel_logger():
    logger = logging.getLogger("creator_atlas")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(OTELJsonFormatter())
        logger.addHandler(handler)
    return logger

otel_logger = get_otel_logger()
