"""Application settings loaded from environment via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from foundrykit.config import FoundrySettings


class AppSettings(FoundrySettings):
    """Backend configuration extending FoundrySettings with app-specific fields."""
    app_name: str = "agentic-template-backend"
    api_port: int = 8001
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    storage_mode: Literal["inmemory", "cosmos"] = "inmemory"
    cosmos_endpoint: str = ""
    cosmos_database_name: str = "agentic-template"
    cosmos_container_messages: str = "messages"
    cosmos_container_sessions: str = "sessions"

    otel_exporter: Literal["console", "otlp", "azure"] = "console"
    otel_service_name: str = "app-template-backend"
    otel_collector_endpoint: str = "http://localhost:4318/v1/traces"
    applicationinsights_connection_string: str = ""

    mcp_server_url: str = "http://localhost:8080/mcp"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()
