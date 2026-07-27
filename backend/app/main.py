import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database.session import engine, init_db
from app.observability.tracer import (
    configure_observability, elapsed_ms, otel_logger, request_id_context,
)
from app.observability.prometheus_metrics import (
    http_requests_total, http_request_duration, http_errors_total,
    start_metrics_server, init_app_info
)

# Initialise providers/exporters before routes import application telemetry objects.
configure_observability(engine)
from app.api.router import api_router  # noqa: E402

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Add Prometheus instrumentation before routes
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


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
        return response
    except Exception as error:
        status_code = 500
        http_errors_total.labels(
            method=request.method,
            endpoint=route,
            error_type=type(error).__name__
        ).inc()
        otel_logger.exception("Unhandled HTTP request error", extra={"endpoint": route, "error_details": str(error)})
        raise
    finally:
        duration = elapsed_ms(started) / 1000  # Convert to seconds for Prometheus
        http_requests_total.labels(
            method=request.method,
            endpoint=route,
            status=status_code
        ).inc()
        http_request_duration.labels(
            method=request.method,
            endpoint=route
        ).observe(duration)
        if status_code >= 400:
            http_errors_total.labels(
                method=request.method,
                endpoint=route,
                error_type=f"status_{status_code}"
            ).inc()
        otel_logger.info("HTTP request completed", extra={"endpoint": route, "execution_time_ms": round(duration * 1000, 2)})
        request_id_context.reset(token)


@app.on_event("startup")
def startup_event():
    init_db()
    init_app_info()
    print(f"Prometheus metrics available at http://localhost:8000/metrics")


@app.on_event("shutdown")
def shutdown_event():
    pass


app.include_router(api_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
