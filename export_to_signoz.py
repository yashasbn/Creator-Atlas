#!/usr/bin/env python3
"""
Standalone script to export metrics/traces from Creator-Atlas to external SigNoz.

This script is completely independent of the application and can be run separately
to send telemetry data to an external SigNoz instance.

Usage:
    python export_to_signoz.py --signoz-endpoint localhost:4317 --service-name creator-atlas
"""
import argparse
import json
import logging
import time
from typing import Optional
from datetime import datetime

try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:
    print("Error: OpenTelemetry libraries not installed.")
    print("Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SigNozExporter:
    """Standalone exporter to send metrics/traces to external SigNoz."""
    
    def __init__(self, signoz_endpoint: str, service_name: str, insecure: bool = True):
        """
        Initialize the SigNoz exporter.
        
        Args:
            signoz_endpoint: External SigNoz OTLP endpoint (e.g., "localhost:4317")
            service_name: Name of the service sending telemetry
            insecure: Whether to use insecure connection (no TLS)
        """
        self.signoz_endpoint = signoz_endpoint
        self.service_name = service_name
        self.insecure = insecure
        self.tracer = None
        self.meter = None
        
        self._setup_telemetry()
    
    def _setup_telemetry(self):
        """Setup OpenTelemetry SDK for traces and metrics."""
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": "standalone-exporter",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })
        
        # Setup trace provider
        trace_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(
            endpoint=self.signoz_endpoint,
            insecure=self.insecure,
            timeout=10,
        )
        trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(trace_provider)
        self.tracer = trace.get_tracer(__name__)
        
        # Setup metrics provider
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=self.signoz_endpoint,
                insecure=self.insecure,
                timeout=10,
            ),
            export_interval_millis=15000
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
        self.meter = metrics.get_meter(__name__)
        
        logger.info(f"Telemetry configured for {self.service_name} -> {self.signoz_endpoint}")
    
    def export_sample_trace(self, operation_name: str, attributes: dict):
        """
        Export a sample trace to SigNoz.
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes for the span
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            span.set_attribute("exported_at", datetime.utcnow().isoformat())
        
        logger.info(f"Exported trace: {operation_name}")
    
    def export_sample_metric(self, metric_name: str, value: float, attributes: dict):
        """
        Export a sample metric to SigNoz.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            attributes: Additional attributes for the metric
        """
        counter = self.meter.create_counter(
            metric_name,
            description=f"Sample counter for {metric_name}"
        )
        counter.add(value, attributes)
        
        logger.info(f"Exported metric: {metric_name} = {value}")
    
    def export_custom_data(self, data: dict):
        """
        Export custom data as traces/metrics to SigNoz.
        
        Args:
            data: Dictionary containing custom telemetry data
        """
        operation = data.get("operation", "custom_operation")
        attributes = data.get("attributes", {})
        
        # Export as trace
        self.export_sample_trace(operation, attributes)
        
        # Export as metric if value is present
        if "value" in data:
            self.export_sample_metric(
                f"{operation}_counter",
                data["value"],
                attributes
            )


def main():
    """Main entry point for the standalone exporter."""
    parser = argparse.ArgumentParser(
        description="Export metrics/traces from Creator-Atlas to external SigNoz"
    )
    parser.add_argument(
        "--signoz-endpoint",
        default="localhost:4317",
        help="External SigNoz OTLP endpoint (default: localhost:4317)"
    )
    parser.add_argument(
        "--service-name",
        default="creator-atlas-standalone",
        help="Service name for telemetry (default: creator-atlas-standalone)"
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=True,
        help="Use insecure connection (default: True)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run with sample test data"
    )
    parser.add_argument(
        "--data-file",
        help="JSON file containing custom telemetry data to export"
    )
    
    args = parser.parse_args()
    
    # Initialize exporter
    exporter = SigNozExporter(
        signoz_endpoint=args.signoz_endpoint,
        service_name=args.service_name,
        insecure=args.insecure
    )
    
    if args.test:
        # Export sample test data
        logger.info("Running test export...")
        
        # Sample trace
        exporter.export_sample_trace(
            "test_operation",
            {
                "test.attribute": "test_value",
                "test.category": "standalone_exporter"
            }
        )
        
        # Sample metric
        exporter.export_sample_metric(
            "test_counter",
            42.0,
            {
                "test.attribute": "test_value",
                "test.category": "standalone_exporter"
            }
        )
        
        logger.info("Test export completed. Check SigNoz UI for data.")
        logger.info(f"SigNoz UI typically available at: http://{args.signoz_endpoint.split(':')[0]}:3301")
        
        # Keep alive for a moment to ensure export
        time.sleep(2)
    
    elif args.data_file:
        # Export data from file
        try:
            with open(args.data_file, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    exporter.export_custom_data(item)
            else:
                exporter.export_custom_data(data)
            
            logger.info(f"Exported data from {args.data_file}")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to export data from file: {e}")
    
    else:
        # Interactive mode
        logger.info("Interactive mode - press Ctrl+C to exit")
        logger.info("Example: export_sample_trace('my_operation', {'key': 'value'})")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Exporter stopped")


if __name__ == "__main__":
    main()
