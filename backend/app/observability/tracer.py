"""OpenTelemetry bootstrap and application-level telemetry primitives.

This module is the only place that configures SDK providers/exporters.  Import the
instruments from here; call ``configure_observability`` once, before importing
routes, in ``app.main``.
"""
import json
import logging
import os
from contextvars import ContextVar
from typing import Any, Mapping, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from app.config import settings

request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_configured = False


class OTELJsonFormatter(logging.Formatter):
    """Emit JSON to stdout so the Collector can correlate logs with traces."""

    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": settings.OTEL_SERVICE_NAME,
            "request_id": getattr(record, "request_id", request_id_context.get()),
            "trace_id": f"{context.trace_id:032x}" if context.is_valid else None,
            "span_id": f"{context.span_id:016x}" if context.is_valid else None,
            "endpoint": getattr(record, "endpoint", None),
            "channel_searched": getattr(record, "channel", None),
            "provider": getattr(record, "provider", None),
            "execution_time_ms": getattr(record, "execution_time_ms", None),
        }
        if record.exc_info:
            payload["error_details"] = self.formatException(record.exc_info)
        elif hasattr(record, "error_details"):
            payload["error_details"] = record.error_details
        # Keep the correlation schema stable for every event; unavailable context is null.
        return json.dumps(payload)


def get_otel_logger() -> logging.Logger:
    logger = logging.getLogger("creator_atlas")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(OTELJsonFormatter())
        logger.addHandler(handler)
    return logger


otel_logger = get_otel_logger()


def configure_observability(sqlalchemy_engine=None) -> None:
    """Configure OTLP and library instrumentation exactly once per process."""
    global _configured
    if _configured:
        return

    # Use custom exporter if remote SigNoz endpoint is configured
    if settings.REMOTE_SIGNOZ_ENDPOINT:
        from app.observability.custom_exporter import configure_custom_exporter
        configure_custom_exporter(
            remote_signoz_endpoint=settings.REMOTE_SIGNOZ_ENDPOINT,
            insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
        )
    else:
        # Use standard local exporter
        resource = Resource.create({
            SERVICE_NAME: settings.OTEL_SERVICE_NAME,
            SERVICE_VERSION: settings.SERVICE_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        })
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)

        reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    # Framework/library spans use OTel semantic conventions and W3C trace context.
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
    if sqlalchemy_engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine)
    _configured = True


tracer = trace.get_tracer("creator_atlas.application", settings.SERVICE_VERSION)
meter = metrics.get_meter("creator_atlas.application", settings.SERVICE_VERSION)

# Low-cardinality attributes only: route/provider/status/cache.operation, never key or raw error text.
http_requests_total = meter.create_counter("creator_atlas.http.server.requests", unit="{request}")
http_request_duration = meter.create_histogram("creator_atlas.http.server.duration", unit="ms")
http_errors_total = meter.create_counter("creator_atlas.http.server.errors", unit="{error}")
cache_operations_total = meter.create_counter("creator_atlas.cache.operations", unit="{operation}")
cache_latency = meter.create_histogram("creator_atlas.cache.duration", unit="ms")
youtube_api_failures = meter.create_counter("creator_atlas.youtube.api.failures", unit="{failure}")
youtube_api_duration = meter.create_histogram("creator_atlas.youtube.api.duration", unit="ms")
llm_requests_total = meter.create_counter("creator_atlas.llm.requests", unit="{request}")
llm_failures_total = meter.create_counter("creator_atlas.llm.failures", unit="{failure}")
llm_latency = meter.create_histogram("creator_atlas.llm.duration", unit="ms")
analytics_duration = meter.create_histogram("creator_atlas.analytics.duration", unit="ms")
response_generation_duration = meter.create_histogram("creator_atlas.response.generation.duration", unit="ms")


def mark_error(span, error: Exception) -> None:
    span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, str(error)))


def elapsed_ms(start: float) -> float:
    import time
    return (time.perf_counter() - start) * 1000
