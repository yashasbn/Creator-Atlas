from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from app.config import settings

# Resource identification for SigNoz / OpenTelemetry
resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
provider = TracerProvider(resource=resource)

# Console / Batch exporter fallback
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

trace.set_tracer_provider(provider)
tracer = trace.get_tracer("creator-atlas", "1.0.0")

