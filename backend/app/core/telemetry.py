"""
OpenTelemetry configuration and setup for observability.
"""
import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from prometheus_client import start_http_server

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelemetryConfig:
    """OpenTelemetry configuration and setup."""
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        
        # Metrics
        self.request_counter: Optional[metrics.Counter] = None
        self.request_duration: Optional[metrics.Histogram] = None
        self.database_query_counter: Optional[metrics.Counter] = None
        self.database_query_duration: Optional[metrics.Histogram] = None
        self.error_counter: Optional[metrics.Counter] = None
    
    def setup_resource(self) -> Resource:
        """Create OpenTelemetry resource with service information."""
        return Resource.create({
            ResourceAttributes.SERVICE_NAME: "expense-tracker-api",
            ResourceAttributes.SERVICE_VERSION: "1.0.0",
            ResourceAttributes.SERVICE_NAMESPACE: "expense-tracker",
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: "development" if settings.debug else "production",
        })
    
    def setup_tracing(self) -> None:
        """Configure OpenTelemetry tracing."""
        resource = self.setup_resource()
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        
        logger.info("OpenTelemetry tracing configured")
    
    def setup_metrics(self) -> None:
        """Configure OpenTelemetry metrics."""
        resource = self.setup_resource()
        
        # Create Prometheus metric reader
        prometheus_reader = PrometheusMetricReader()
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader]
        )
        metrics.set_meter_provider(self.meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self.request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        self.request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        self.database_query_counter = self.meter.create_counter(
            name="database_queries_total",
            description="Total number of database queries",
            unit="1"
        )
        
        self.database_query_duration = self.meter.create_histogram(
            name="database_query_duration_seconds",
            description="Database query duration in seconds",
            unit="s"
        )
        
        self.error_counter = self.meter.create_counter(
            name="errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        # Start Prometheus metrics server
        prometheus_port = int(os.getenv("PROMETHEUS_PORT", "8000"))
        start_http_server(prometheus_port)
        
        logger.info(f"OpenTelemetry metrics configured, Prometheus server on port {prometheus_port}")
    
    def setup_instrumentation(self, app) -> None:
        """Configure automatic instrumentation."""
        # FastAPI instrumentation
        FastAPIInstrumentor.instrument_app(app)
        
        # SQLAlchemy instrumentation
        SQLAlchemyInstrumentor().instrument()
        
        # AsyncPG instrumentation
        AsyncPGInstrumentor().instrument()
        
        # Requests instrumentation
        RequestsInstrumentor().instrument()
        
        logger.info("OpenTelemetry instrumentation configured")
    
    def initialize(self, app) -> None:
        """Initialize all OpenTelemetry components."""
        try:
            self.setup_tracing()
            self.setup_metrics()
            self.setup_instrumentation(app)
            logger.info("OpenTelemetry initialization completed successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            raise


# Global telemetry instance
telemetry = TelemetryConfig()


def get_tracer() -> trace.Tracer:
    """Get the configured tracer."""
    if telemetry.tracer is None:
        raise RuntimeError("Telemetry not initialized. Call telemetry.initialize() first.")
    return telemetry.tracer


def get_meter() -> metrics.Meter:
    """Get the configured meter."""
    if telemetry.meter is None:
        raise RuntimeError("Telemetry not initialized. Call telemetry.initialize() first.")
    return telemetry.meter


def record_request_metrics(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record HTTP request metrics."""
    if telemetry.request_counter and telemetry.request_duration:
        attributes = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        }
        telemetry.request_counter.add(1, attributes)
        telemetry.request_duration.record(duration, attributes)


def record_database_metrics(operation: str, table: str, duration: float) -> None:
    """Record database operation metrics."""
    if telemetry.database_query_counter and telemetry.database_query_duration:
        attributes = {
            "operation": operation,
            "table": table
        }
        telemetry.database_query_counter.add(1, attributes)
        telemetry.database_query_duration.record(duration, attributes)


def record_error_metrics(error_type: str, endpoint: str) -> None:
    """Record error metrics."""
    if telemetry.error_counter:
        attributes = {
            "error_type": error_type,
            "endpoint": endpoint
        }
        telemetry.error_counter.add(1, attributes)