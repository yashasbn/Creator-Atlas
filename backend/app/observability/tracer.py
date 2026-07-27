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
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
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
            "service": settings.PROJECT_NAME,
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
    """Configure OpenTelemetry and library instrumentation exactly once per process."""
    global _configured
    if _configured:
        return

    # Configure resource
    resource = Resource.create({
        SERVICE_NAME: settings.PROJECT_NAME,
        SERVICE_VERSION: settings.SERVICE_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })
    
    # Configure trace provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configure metrics provider (will be replaced by Prometheus)
    metrics.set_meter_provider(MeterProvider(resource=resource))

    # Framework/library spans use OTel semantic conventions and W3C trace context.
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    def scrub_api_keys(span, request_obj):
        if not span or not request_obj:
            return
        url = getattr(request_obj, "url", None)
        if not url:
            return
        if "key=" in url:
            import urllib.parse
            try:
                parsed = urllib.parse.urlparse(url)
                q = urllib.parse.parse_qs(parsed.query)
                if "key" in q:
                    q["key"] = ["REDACTED"]
                new_query = urllib.parse.urlencode(q, doseq=True)
                scrubbed_url = urllib.parse.urlunparse(
                    (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
                )
                span.set_attribute("http.url", scrubbed_url)
            except Exception:
                pass

    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    RequestsInstrumentor().instrument(request_hook=scrub_api_keys)
    RedisInstrumentor().instrument()
    if sqlalchemy_engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine)
    _configured = True


tracer = trace.get_tracer("creator_atlas.application", settings.SERVICE_VERSION)


def mark_error(span, error: Exception) -> None:
    span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, str(error)))


def elapsed_ms(start: float) -> float:
    import time
    return (time.perf_counter() - start) * 1000
