"""OpenTelemetry tracing configuration with console, OTLP, and Azure Monitor modes."""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from core.config import AppSettings


def configure_tracing(settings: AppSettings) -> None:
    """Initialize TracerProvider with the exporter mode specified in settings."""
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter == "console":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif settings.otel_exporter == "otlp":
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_collector_endpoint))
        )
    else:
        # Keep the dependency optional in practice; this mode is enabled in cloud deployments.
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        provider.add_span_processor(
            BatchSpanProcessor(
                AzureMonitorTraceExporter.from_connection_string(
                    settings.applicationinsights_connection_string
                )
            )
        )

    trace.set_tracer_provider(provider)


def instrument_fastapi(app: FastAPI) -> None:
    """Attach OpenTelemetry auto-instrumentation to a FastAPI app."""
    FastAPIInstrumentor.instrument_app(app)
