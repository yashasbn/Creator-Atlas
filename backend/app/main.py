import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.config import settings
from app.database.session import engine, init_db
from app.observability.tracer import (
    configure_observability, elapsed_ms, http_errors_total, http_request_duration,
    http_requests_total, otel_logger, request_id_context,
)

# Initialise providers/exporters before routes import application telemetry objects.
configure_observability(engine)
from app.api.router import api_router  # noqa: E402

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Adds request correlation and RED metrics around every response, including errors."""
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_context.set(request_id)
    route = request.url.path
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        from opentelemetry import trace
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            trace_id = f"{span_context.trace_id:032x}"
            response.headers["X-Trace-ID"] = trace_id
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Trace-ID"
        return response
    except Exception as error:
        status_code = 500
        http_errors_total.add(1, {"http.route": route, "error.type": type(error).__name__})
        otel_logger.exception("Unhandled HTTP request error", extra={"endpoint": route, "error_details": str(error)})
        raise
    finally:
        duration = elapsed_ms(started)
        attributes = {"http.route": route, "http.request.method": request.method, "http.response.status_code": status_code}
        http_requests_total.add(1, attributes)
        http_request_duration.record(duration, attributes)
        if status_code >= 400:
            http_errors_total.add(1, {"http.route": route, "http.response.status_code": status_code})
        otel_logger.info("HTTP request completed", extra={"endpoint": route, "execution_time_ms": round(duration, 2)})
        request_id_context.reset(token)


@app.on_event("startup")
def startup_event():
    init_db()


@app.on_event("shutdown")
def shutdown_event():
    from opentelemetry import trace
    trace.get_tracer_provider().shutdown()


# Add OTel last so its ASGI middleware wraps the correlation middleware and every
# completion log has the active server span context.
FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
app.include_router(api_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
