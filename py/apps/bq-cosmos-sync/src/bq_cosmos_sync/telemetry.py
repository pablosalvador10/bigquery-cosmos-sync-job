"""OpenTelemetry setup. Exports to App Insights when the connection string is set."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager, suppress

from opentelemetry import trace
from opentelemetry.trace import Span

logger = logging.getLogger(__name__)


def configure_telemetry(*, service_name: str, connection_string: str | None) -> None:
    if not connection_string:
        logger.debug("Application Insights connection string not set — telemetry disabled")
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=connection_string,
            resource_attributes={"service.name": service_name},
            enable_live_metrics=False,
        )
        logger.info("Azure Monitor OpenTelemetry exporter configured")
    except Exception:  # noqa: BLE001 — telemetry must never break the run
        logger.warning("Failed to configure Azure Monitor exporter", exc_info=True)


_tracer = trace.get_tracer("bq_cosmos_sync")


@contextmanager
def span(name: str, **attrs: object) -> Iterator[Span]:
    with _tracer.start_as_current_span(name) as s:
        for k, v in attrs.items():
            with suppress(Exception):
                s.set_attribute(k, v)  # type: ignore[arg-type]
        yield s
