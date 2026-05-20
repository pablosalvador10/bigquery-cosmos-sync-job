---
name: observability-setup
description: 'Configures OpenTelemetry tracing, structured logging, and Azure Application Insights. Use when setting up observability, adding custom spans, configuring tracing exporters, connecting to App Insights, or debugging performance issues.'
argument-hint: 'Describe the observability task (e.g., "add custom span to agent calls", "connect to App Insights", "switch to OTLP collector")'
---

## Purpose
Guide for configuring and extending the observability stack: OpenTelemetry tracing, structlog logging, and Azure Monitor / Application Insights integration.

## When to Use
- Setting up tracing for a new deployment.
- Adding custom spans to application code.
- Switching between tracing exporters (console, OTLP, Azure).
- Connecting to Application Insights.
- Debugging latency or performance issues.

## Architecture

```
App Code
  │
  ├─ structlog (logging)         → stdout (console/JSON based on TTY)
  │
  ├─ OpenTelemetry SDK (tracing) → configured in core/telemetry.py
  │   ├─ console exporter        → stdout (local dev)
  │   ├─ OTLP exporter           → collector endpoint (self-hosted)
  │   └─ Azure Monitor exporter  → Application Insights (production)
  │
  └─ FastAPI auto-instrumentation → request/response spans
      └─ ToolRegistry spans       → tool.{name} per tool call
```

## Configuration

Controlled by environment variables in `.env`:

| Variable | Values | Purpose |
|----------|--------|---------|
| `OTEL_EXPORTER` | `console`, `otlp`, `azure` | Selects the trace exporter |
| `OTEL_SERVICE_NAME` | any string | Service name in traces (default: `app-template-backend`) |
| `OTEL_COLLECTOR_ENDPOINT` | URL | OTLP collector endpoint (when `OTEL_EXPORTER=otlp`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | connection string | App Insights key (when `OTEL_EXPORTER=azure`) |

## How It Works

### Initialization (`core/telemetry.py`)

At app startup (`main.py` lifespan), `configure_tracing(settings)` is called:

```python
def configure_tracing(settings: AppSettings) -> None:
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter == "console":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif settings.otel_exporter == "otlp":
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_collector_endpoint))
        )
    else:  # azure
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        provider.add_span_processor(
            BatchSpanProcessor(
                AzureMonitorTraceExporter.from_connection_string(
                    settings.applicationinsights_connection_string
                )
            )
        )
    trace.set_tracer_provider(provider)
```

### Auto-Instrumentation

`instrument_fastapi(app)` adds automatic spans for every HTTP request/response.

### Tool Tracing (`ToolRegistry`)

Every `@registry.register` decorated tool gets an OpenTelemetry span:
- Span name: `tool.{function_name}`
- Attribute: `tool.name = "{function_name}"`

## Flow: Adding Custom Spans

### Step 1: Get a tracer
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
```

### Step 2: Create spans
```python
# Option A: Context manager
with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("input.length", len(data))
    result = do_something(data)
    span.set_attribute("output.status", "success")

# Option B: Decorator (for functions)
@tracer.start_as_current_span("process_message")
def process_message(msg: str) -> str:
    ...
```

### Step 3: Add attributes for debugging
```python
span.set_attribute("session.id", session_id)
span.set_attribute("agent.name", spec.name)
span.set_attribute("tool.count", len(spec.tools))
```

## Flow: Connecting to Application Insights

### Step 1: Get connection string
From Terraform output or Azure portal → Application Insights → Connection String.

### Step 2: Configure environment
```env
OTEL_EXPORTER=azure
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...
```

### Step 3: Install exporter (if not already)
```bash
uv pip install azure-monitor-opentelemetry-exporter
```

### Step 4: Verify in Azure portal
- Open Application Insights → Transaction search
- Look for traces from `OTEL_SERVICE_NAME`
- Tool calls appear as `tool.{name}` spans
- HTTP requests appear as `GET /healthz`, `POST /api/v1/chat/stream`, etc.

## Flow: Structured Logging (`core/logging.py`)

structlog is configured at startup via `configure_logging(settings.log_level)`:
- **TTY (local dev)**: colored console output via `ConsoleRenderer`
- **Non-TTY (container/CI)**: JSON output via `JSONRenderer`

Usage in application code:
```python
from core.logging import logger

logger.info("chat_stream_complete", session_id=body.session_id)
logger.error("agent_failed", error=str(e), agent_name=spec.name)
```

Structured fields become searchable in Log Analytics when combined with Azure Monitor.

## Decision Logic

| Scenario | `OTEL_EXPORTER` | Notes |
|----------|-----------------|-------|
| Local development | `console` | Spans print to stdout |
| Self-hosted collector (Jaeger, Zipkin) | `otlp` | Set `OTEL_COLLECTOR_ENDPOINT` |
| Azure production | `azure` | Set `APPLICATIONINSIGHTS_CONNECTION_STRING` |
| Disable tracing | (not supported) | Remove `configure_tracing()` call from lifespan |

## Checklist
- [ ] `OTEL_EXPORTER` set in `.env` (default: `console`)
- [ ] `OTEL_SERVICE_NAME` set to identify your app
- [ ] For Azure: `APPLICATIONINSIGHTS_CONNECTION_STRING` populated
- [ ] `configure_tracing()` called in `main.py` lifespan
- [ ] `instrument_fastapi(app)` called after app creation
- [ ] Custom spans use `trace.get_tracer(__name__)` (not global tracer)
- [ ] Tool functions registered with `@registry.register` (auto-traced)
- [ ] Verify traces appear in console or Azure portal
