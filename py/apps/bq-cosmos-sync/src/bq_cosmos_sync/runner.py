"""Pipeline orchestration. Reads watermarks, runs pipelines, writes summaries."""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ms.fde.bigquerykit import BigQueryDataset

from bq_cosmos_sync.checkpoint import CheckpointStore
from bq_cosmos_sync.cosmos.writer import BatchWriter
from bq_cosmos_sync.logging import log_event
from bq_cosmos_sync.models import PipelineStatus, PipelineSummary, RunStatus, RunSummary
from bq_cosmos_sync.pipelines.base import Pipeline, PipelineContext
from bq_cosmos_sync.telemetry import span

logger = logging.getLogger(__name__)

WriterFactory = Callable[[str], BatchWriter]


class SyncRunner:
    def __init__(
        self,
        *,
        bq_dataset: BigQueryDataset,
        get_writer: WriterFactory,
        checkpoint_store: CheckpointStore,
        pipelines: list[Pipeline],
        project_id: str,
        dataset: str,
        run_id: str | None = None,
        batch_size: int = 500,
        dry_run: bool = False,
        fail_fast: bool = False,
        max_parallel_pipelines: int = 1,
    ) -> None:
        if not pipelines:
            msg = "At least one pipeline must be provided"
            raise ValueError(msg)
        self._bq = bq_dataset
        self._get_writer = get_writer
        self._checkpoints = checkpoint_store
        self._pipelines = pipelines
        self._project_id = project_id
        self._dataset = dataset
        self._run_id = run_id or _generate_run_id()
        self._batch_size = batch_size
        self._dry_run = dry_run
        self._fail_fast = fail_fast
        self._sem = asyncio.Semaphore(max_parallel_pipelines)

    @property
    def run_id(self) -> str:
        return self._run_id

    async def run(self) -> RunSummary:
        started = time.perf_counter()
        summary = RunSummary(run_id=self._run_id, status="success")
        log_event(
            logger,
            "sync.run.started",
            runId=self._run_id,
            pipelines=[p.name for p in self._pipelines],
            dryRun=self._dry_run,
        )

        if self._max_parallel_pipelines == 1:
            for pipeline in self._pipelines:
                ps = await self._run_pipeline(pipeline)
                summary.pipelines.append(ps)
                if ps.status == "failed" and self._fail_fast:
                    log_event(logger, "sync.run.fail_fast", failedPipeline=pipeline.name)
                    break
        else:
            results = await asyncio.gather(
                *(self._guarded(p) for p in self._pipelines),
                return_exceptions=False,
            )
            summary.pipelines.extend(results)

        summary.finished_at = datetime.now(UTC)
        summary.duration_seconds = round(time.perf_counter() - started, 3)
        summary.status = _rollup_status(summary)
        log_event(
            logger,
            "sync.run.completed",
            runId=self._run_id,
            status=summary.status,
            rowsRead=summary.rows_read,
            rowsUpserted=summary.rows_upserted,
            rowsFailed=summary.rows_failed,
            durationSeconds=summary.duration_seconds,
            pipelines=[p.model_dump(mode="json") for p in summary.pipelines],
        )
        return summary

    @property
    def _max_parallel_pipelines(self) -> int:
        return self._sem._value  # type: ignore[attr-defined]

    async def _guarded(self, pipeline: Pipeline) -> PipelineSummary:
        async with self._sem:
            return await self._run_pipeline(pipeline)

    async def _run_pipeline(self, pipeline: Pipeline) -> PipelineSummary:
        started_perf = time.perf_counter()
        started_at = datetime.now(UTC)
        log_event(logger, "sync.pipeline.started", pipeline=pipeline.name)

        watermark_before: datetime | None = None
        if pipeline.refresh_mode == "incremental":
            watermark_before = await self._checkpoints.read_watermark(pipeline.name)

        ctx = PipelineContext(
            project_id=self._project_id,
            dataset=self._dataset,
            run_id=self._run_id,
            watermark=watermark_before,
        )

        result = PipelineSummary(
            pipeline_name=pipeline.name,
            status="success",
            started_at=started_at,
            watermark_before=watermark_before,
        )

        new_watermark: datetime | None = watermark_before
        try:
            with span("pipeline", pipeline=pipeline.name, refresh_mode=pipeline.refresh_mode):
                writer = self._get_writer(pipeline.container_name) if not self._dry_run else None

                async for batch in self._bq.query_rows(
                    pipeline.build_query(ctx),
                    page_size=self._batch_size,
                ):
                    result.rows_read += len(batch)

                    documents: list[dict[str, Any]] = []
                    for row in batch:
                        try:
                            doc = pipeline.row_to_document(row, ctx=ctx)
                            _validate_document(doc, pipeline.partition_key_field)
                            documents.append(doc)
                            wm = pipeline.extract_watermark(row)
                            if wm is not None and (new_watermark is None or wm > new_watermark):
                                new_watermark = wm
                        except Exception as exc:  # noqa: BLE001 — per-row isolation
                            result.rows_failed += 1
                            logger.warning(
                                "Row projection failed: %s",
                                exc,
                                extra={
                                    "pipeline": pipeline.name,
                                    "event": "sync.row.failed",
                                },
                            )

                    if writer is not None and documents:
                        batch_result = await writer.upsert_batch(documents)
                        result.rows_upserted += batch_result.upserted
                        result.rows_failed += batch_result.failed
                        if batch_result.failures:
                            log_event(
                                logger,
                                "sync.pipeline.batch_failures",
                                level=logging.WARNING,
                                pipeline=pipeline.name,
                                sample=batch_result.failures[:5],
                            )

        except Exception as exc:
            result.status = "failed"
            result.error_type = type(exc).__name__
            result.error_message = str(exc)
            logger.exception(
                "Pipeline failed",
                extra={
                    "pipeline": pipeline.name,
                    "event": "sync.pipeline.failed",
                },
            )
        finally:
            result.finished_at = datetime.now(UTC)
            result.duration_seconds = round(time.perf_counter() - started_perf, 3)
            if result.status != "failed" and result.rows_failed > 0:
                result.status = "partial"
            result.watermark_after = new_watermark
            if not self._dry_run:
                # Only advance watermark on success/partial, not on hard failure.
                advance_to = new_watermark if result.status in ("success", "partial") else watermark_before
                try:
                    await self._checkpoints.write_summary(
                        result,
                        run_id=self._run_id,
                        new_watermark=advance_to,
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist checkpoint",
                        extra={
                            "pipeline": pipeline.name,
                            "event": "sync.checkpoint.failed",
                        },
                    )

        log_event(
            logger,
            "sync.pipeline.completed",
            pipeline=pipeline.name,
            status=result.status,
            rowsRead=result.rows_read,
            rowsUpserted=result.rows_upserted,
            rowsFailed=result.rows_failed,
            durationSeconds=result.duration_seconds,
        )
        return result


def _rollup_status(summary: RunSummary) -> RunStatus:
    statuses: list[PipelineStatus] = [p.status for p in summary.pipelines]
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s == "partial" for s in statuses) or summary.rows_failed > 0:
        return "partial"
    return "success"


def _validate_document(doc: dict[str, Any], partition_key_field: str) -> None:
    if "id" not in doc or not str(doc["id"]):
        msg = "Document missing required 'id'"
        raise ValueError(msg)
    if partition_key_field not in doc or doc[partition_key_field] in (None, ""):
        msg = f"Document missing partition key field {partition_key_field!r}"
        raise ValueError(msg)


def _generate_run_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
