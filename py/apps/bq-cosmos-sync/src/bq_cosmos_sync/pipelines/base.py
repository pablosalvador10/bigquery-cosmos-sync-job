"""Pipeline protocol. Pure data, no I/O. The runner injects clients."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

RefreshMode = Literal["full", "incremental"]


class PipelineContext(BaseModel):
    """Read-only context passed into every pipeline call."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    dataset: str
    run_id: str
    watermark: datetime | None = None


class Pipeline(ABC):
    name: str
    container_name: str
    partition_key_field: str
    refresh_mode: RefreshMode = "full"
    watermark_column: str | None = None

    @abstractmethod
    def build_query(self, ctx: PipelineContext) -> str: ...

    @abstractmethod
    def row_to_document(self, row: dict[str, Any], *, ctx: PipelineContext) -> dict[str, Any]: ...

    def extract_watermark(self, row: dict[str, Any]) -> datetime | None:
        if not self.watermark_column:
            return None
        value = row.get(self.watermark_column)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None
