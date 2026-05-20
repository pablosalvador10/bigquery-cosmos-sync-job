"""Environment-driven settings."""

from typing import Annotated

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
    # Auth is Microsoft Entra ID (managed identity in Azure, az login locally)
    # by default. The IaC disables shared-key authentication on the Cosmos
    # account, so production deployments cannot use keys even if they wanted
    # to. The cosmos_emulator_key escape hatch is for the local Cosmos
    # emulator (docker-compose) only. See docs/identity.md.
    cosmos_endpoint: str = Field(..., description="https://<acct>.documents.azure.com:443/")
    cosmos_database: str = Field("learnsphere")
    cosmos_verify_tls: bool = True
    cosmos_upsert_concurrency: int = Field(16, ge=1, le=256)
    cosmos_batch_size: int = Field(500, ge=1, le=10_000)
    cosmos_emulator_key: str | None = Field(
        default=None,
        description="Emulator-only shared key. Refused for non-emulator endpoints by validate_runtime().",
    )

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
        if self.cosmos_emulator_key:
            host = self.cosmos_endpoint.split("/", 3)[2].split(":", 1)[0].lower()
            if host not in {"localhost", "127.0.0.1", "cosmos-emulator"}:
                msg = (
                    "cosmos_emulator_key is only valid for the local Cosmos emulator "
                    f"(localhost / cosmos-emulator); got endpoint host {host!r}. "
                    "Production deployments must use Microsoft Entra ID."
                )
                raise ValueError(msg)


def load_settings() -> Settings:
    s = Settings()  # type: ignore[call-arg]
    s.validate_runtime()
    return s
