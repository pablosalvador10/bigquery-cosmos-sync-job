"""Environment-driven settings."""

from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- BigQuery
    bq_project_id: str = Field(..., description="GCP project hosting the dataset")
    bq_dataset: str = Field("learnsphere")
    bq_location: str = Field("US")

    # ---- Cosmos
    cosmos_endpoint: str = Field(..., description="https://<acct>.documents.azure.com:443/")
    cosmos_database: str = Field("learnsphere")
    cosmos_auth_mode: Literal["managed_identity", "key"] = "managed_identity"
    cosmos_key: str | None = None
    cosmos_verify_tls: bool = True
    cosmos_upsert_concurrency: int = Field(16, ge=1, le=256)
    cosmos_batch_size: int = Field(500, ge=1, le=10_000)

    # ---- Sync orchestration
    sync_run_id: str | None = None
    # NoDecode: keep the raw env string; our validator splits CSV.
    sync_pipelines: Annotated[list[str], NoDecode] = Field(default_factory=list)
    sync_dry_run: bool = False
    sync_max_parallel_pipelines: int = Field(1, ge=1, le=16)
    sync_fail_fast: bool = False

    # ---- Identity / observability
    azure_client_id: str | None = None
    applicationinsights_connection_string: str | None = None
    otel_service_name: str = "bq-cosmos-sync"
    log_level: str = "INFO"

    @field_validator("sync_pipelines", mode="before")
    @classmethod
    def _split_pipelines(cls, v: str | list[str] | None) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("cosmos_endpoint")
    @classmethod
    def _strip_trailing_slash_ok(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            msg = "cosmos_endpoint must be an https URL"
            raise ValueError(msg)
        return v

    def validate_runtime(self) -> None:
        """Cross-field checks run on startup; raises ``ValueError`` on misconfig."""
        if self.cosmos_auth_mode == "key" and not self.cosmos_key:
            msg = "COSMOS_KEY is required when COSMOS_AUTH_MODE=key"
            raise ValueError(msg)


def load_settings() -> Settings:
    s = Settings()  # type: ignore[call-arg]
    s.validate_runtime()
    return s
