"""Base configuration for Azure AI Foundry client."""

from typing import Literal

from pydantic_settings import BaseSettings


class FoundrySettings(BaseSettings):
    """Settings for Foundry endpoint, model, and credential mode."""
    foundry_project_endpoint: str = ""
    foundry_model: str = "gpt-4.1-mini"
    foundry_credential_mode: Literal["dev", "managed_identity"] = "dev"
    azure_client_id: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
