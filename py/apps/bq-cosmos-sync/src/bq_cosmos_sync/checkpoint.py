"""Watermarks and run summaries in the ``sync_metadata`` container."""

import logging
from datetime import datetime
from typing import Any

from ms.fde.cosmosdbkit.container import CosmosContainer

from bq_cosmos_sync.models import PipelineSummary

logger = logging.getLogger(__name__)

_SYNC_METADATA_CONTAINER = "sync_metadata"


class CheckpointStore:
    def __init__(self, container: CosmosContainer) -> None:
        self._c = container

    @property
    def container_name(self) -> str:
        return _SYNC_METADATA_CONTAINER

    async def read_watermark(self, pipeline_name: str) -> datetime | None:
        doc = await self._c.try_read_item(item=pipeline_name, partition_key=pipeline_name)
        if doc is None:
            return None
        raw = doc.get("last_watermark")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            logger.warning("Invalid watermark on pipeline=%s: %r", pipeline_name, raw)
            return None

    async def write_summary(
        self,
        summary: PipelineSummary,
        *,
        run_id: str,
        new_watermark: datetime | None,
    ) -> None:
        body: dict[str, Any] = {
            "id": summary.pipeline_name,
            "pipelineName": summary.pipeline_name,
            "last_run_id": run_id,
            "last_status": summary.status,
            "last_started_at": summary.started_at.isoformat(),
            "last_finished_at": (summary.finished_at or summary.started_at).isoformat(),
            "last_duration_seconds": summary.duration_seconds,
            "last_rows_read": summary.rows_read,
            "last_rows_upserted": summary.rows_upserted,
            "last_rows_failed": summary.rows_failed,
            "last_error_type": summary.error_type,
            "last_error_message": summary.error_message,
            "last_watermark": new_watermark.isoformat() if new_watermark else None,
        }
        await self._c.upsert_item(body)
