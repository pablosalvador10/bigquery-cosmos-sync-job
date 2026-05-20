"""Typer CLI: ``bq-cosmos-sync run|list-pipelines``."""

import asyncio
import logging

import typer
from ms.fde.bigquerykit import BigQueryKitClient
from ms.fde.cosmosdbkit.client import CosmosKitClient

from bq_cosmos_sync.checkpoint import CheckpointStore
from bq_cosmos_sync.config import Settings, load_settings
from bq_cosmos_sync.cosmos.writer import BatchWriter
from bq_cosmos_sync.logging import configure_logging, log_event
from bq_cosmos_sync.pipelines.registry import default_registry
from bq_cosmos_sync.runner import SyncRunner
from bq_cosmos_sync.telemetry import configure_telemetry

app = typer.Typer(add_completion=False, help="BigQuery -> Azure Cosmos DB scheduled sync.")
logger = logging.getLogger("bq_cosmos_sync.cli")


EXIT_OK = 0
EXIT_HARD_FAILURE = 1
EXIT_PARTIAL_FAILURE = 2
EXIT_CONFIG_ERROR = 78


@app.command()
def run(
    pipelines: str = typer.Option(
        "",
        "--pipelines",
        "-p",
        help="Comma-separated pipeline names. Empty = all registered.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Read BQ but do not write to Cosmos."),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Stop after first pipeline failure."),
) -> None:
    """Execute the sync."""
    try:
        settings = load_settings()
    except Exception as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(EXIT_CONFIG_ERROR) from exc

    configure_logging(level=settings.log_level, service=settings.otel_service_name)
    configure_telemetry(
        service_name=settings.otel_service_name,
        connection_string=settings.applicationinsights_connection_string,
    )

    cli_pipelines = [p.strip() for p in pipelines.split(",") if p.strip()] or settings.sync_pipelines
    selected = cli_pipelines or None
    effective_dry_run = dry_run or settings.sync_dry_run
    effective_fail_fast = fail_fast or settings.sync_fail_fast

    exit_code = asyncio.run(
        _run_async(
            settings=settings,
            selected=selected,
            dry_run=effective_dry_run,
            fail_fast=effective_fail_fast,
        )
    )
    raise typer.Exit(code=exit_code)


@app.command("list-pipelines")
def list_pipelines() -> None:
    """List pipeline names registered in the default registry."""
    for name in default_registry().names():
        typer.echo(name)


# ----------------------------------------------------------------------- async


async def _run_async(
    *,
    settings: Settings,
    selected: list[str] | None,
    dry_run: bool,
    fail_fast: bool,
) -> int:
    registry = default_registry()
    try:
        pipelines_list = registry.build_many(selected)
    except KeyError as exc:
        log_event(logger, "sync.config.error", level=logging.ERROR, error=str(exc))
        return EXIT_CONFIG_ERROR

    cosmos_kwargs: dict[str, object] = {}
    if settings.cosmos_emulator_key:
        cosmos_kwargs["key"] = settings.cosmos_emulator_key

    cosmos = CosmosKitClient(endpoint=settings.cosmos_endpoint, **cosmos_kwargs)  # type: ignore[arg-type]
    bq = BigQueryKitClient(project=settings.bq_project_id, location=settings.bq_location)

    try:
        async with cosmos, bq:
            checkpoint_container = cosmos.get_container(settings.cosmos_database, "sync_metadata")
            store = CheckpointStore(checkpoint_container)

            def writer_factory(container_name: str) -> BatchWriter:
                return BatchWriter(
                    cosmos.get_container(settings.cosmos_database, container_name),
                    concurrency=settings.cosmos_upsert_concurrency,
                )

            runner = SyncRunner(
                bq_dataset=bq.get_dataset(settings.bq_dataset),
                get_writer=writer_factory,
                checkpoint_store=store,
                pipelines=pipelines_list,
                project_id=settings.bq_project_id,
                dataset=settings.bq_dataset,
                run_id=settings.sync_run_id,
                batch_size=settings.cosmos_batch_size,
                dry_run=dry_run,
                fail_fast=fail_fast,
                max_parallel_pipelines=settings.sync_max_parallel_pipelines,
            )
            summary = await runner.run()
    except Exception as exc:  # noqa: BLE001
        log_event(
            logger,
            "sync.run.completed",
            level=logging.ERROR,
            runId="<startup-failure>",
            status="failed",
            errorType=type(exc).__name__,
            errorMessage=str(exc),
        )
        return EXIT_HARD_FAILURE

    if summary.status == "failed":
        return EXIT_HARD_FAILURE
    if summary.status == "partial":
        return EXIT_PARTIAL_FAILURE
    return EXIT_OK
