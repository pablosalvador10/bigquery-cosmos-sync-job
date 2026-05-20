"""Structured JSON logging — one event per line on stdout.

Container App console logs are scraped into Log Analytics; emitting structured
JSON lets the alert rules in ``infra/modules/monitor-alerts`` parse fields
without regex hacks.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self._service,
            "message": record.getMessage(),
        }
        # Promote any structured extras (e.g. logger.info("...", extra={"event": "..."}))
        for k, v in record.__dict__.items():
            if k in _RESERVED or k.startswith("_"):
                continue
            payload[k] = v
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(*, level: str = "INFO", service: str = "bq-cosmos-sync") -> None:
    """Idempotent: replaces handlers on the root logger with one JSON handler."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service=service))
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Tame noisy library loggers.
    for noisy in ("azure", "urllib3", "google.api_core", "google.auth"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_event(logger: logging.Logger, event: str, /, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured event. Reserved keys (``event``, ``ts``, ...) are merged."""
    logger.log(level, event, extra={"event": event, **fields})
