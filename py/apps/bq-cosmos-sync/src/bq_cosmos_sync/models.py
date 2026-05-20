"""Pydantic models for run + pipeline summaries."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

PipelineStatus = Literal["success", "partial", "failed", "skipped"]
RunStatus = Literal["success", "partial", "failed"]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PipelineSummary(BaseModel):
    pipeline_name: str
    status: PipelineStatus
    rows_read: int = 0
    rows_upserted: int = 0
    rows_failed: int = 0
    duration_seconds: float = 0.0
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    error_type: str | None = None
    error_message: str | None = None
    watermark_before: datetime | None = None
    watermark_after: datetime | None = None


class RunSummary(BaseModel):
    run_id: str
    status: RunStatus
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    duration_seconds: float = 0.0
    pipelines: list[PipelineSummary] = Field(default_factory=list)

    @property
    def rows_read(self) -> int:
        return sum(p.rows_read for p in self.pipelines)

    @property
    def rows_upserted(self) -> int:
        return sum(p.rows_upserted for p in self.pipelines)

    @property
    def rows_failed(self) -> int:
        return sum(p.rows_failed for p in self.pipelines)
