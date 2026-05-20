# bq-cosmos-sync

Python 3.12 async sync job. Reads from BigQuery, upserts into Azure Cosmos DB (NoSQL), writes a checkpoint, exits.

## Layout

```
src/bq_cosmos_sync/
  __main__.py        # python -m bq_cosmos_sync run
  cli.py             # typer entrypoint
  config.py          # pydantic-settings (env-driven)
  logging.py         # JSON logs to stdout
  telemetry.py       # OpenTelemetry + Azure Monitor exporter
  models.py          # Pydantic models for run/pipeline summaries
  runner.py          # SyncRunner — orchestrates pipelines
  checkpoint.py      # CheckpointStore — reads/writes sync_metadata in Cosmos
  bigquery/
    client.py        # Thin async wrapper around google-cloud-bigquery
  cosmos/
    writer.py        # BatchWriter — bounded-concurrency upserts
  pipelines/
    base.py          # Pipeline Protocol + PipelineResult
    registry.py      # name -> Pipeline factory
    learners.py      # incremental by updated_at
    courses.py       # full refresh
    recommendations.py  # full refresh

tests/
  conftest.py
  fakes.py
  test_config.py
  test_runner.py
  test_checkpoint.py
  test_pipelines.py
```

## Run locally

```bash
uv sync --project .
uv run bq-cosmos-sync run --pipelines courses,learners,recommendations
uv run bq-cosmos-sync run --dry-run         # read BQ, skip Cosmos
uv run bq-cosmos-sync list-pipelines
```

## Adding a pipeline

1. Create `src/bq_cosmos_sync/pipelines/your_pipeline.py` subclassing `Pipeline`.
2. Register it in `pipelines/registry.py`.
3. Add a Cosmos container to `infra/main.tf` `local.cosmos_containers`.
4. Set `SYNC_PIPELINES=...` (or leave empty to run all).
