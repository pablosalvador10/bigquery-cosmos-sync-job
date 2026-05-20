# Copilot instructions for `bigquery-cosmos-sync-job`

This repo is a production-ready template: a daily BigQuery → Cosmos DB sync
that runs as an Azure Container App Job. Read these instructions before making
non-trivial changes.

## Repo shape

- `py/apps/bq-cosmos-sync` — the job (Python 3.12, async, Typer CLI).
- `py/libs/bigquerykit` — async wrapper around `google-cloud-bigquery`,
  module `ms.fde.bigquerykit`. Reusable across jobs.
- `py/libs/cosmosdbkit` — async wrapper around `azure-cosmos`,
  module `ms.fde.cosmosdbkit`. Reusable across jobs.
- `infra/` — Terraform root + modules. azd-orchestrated.
- `notebooks/` — LearnSphere sample (seed BQ, validate joins, inspect Cosmos).
- `docs/` — Architecture, decisions, setup, deployment, observability,
  troubleshooting.

## Non-negotiables

- **Python 3.12 only.** `pyproject.toml` pins `==3.12.*`.
- **uv workspace.** Use `uv sync --project py/apps/bq-cosmos-sync`. Never
  `pip install` into the venv.
- **Joins live in BigQuery, not Python.** Pipelines emit SQL via
  `build_query()` and project shaped rows in `row_to_document()`. Do not move
  join logic into the runner or into Python loops.
- **Deterministic document IDs.** `id = "<entity>::<source-pk>"`. Re-runs must
  be idempotent.
- **One row → one document.** No fan-out, no merges. If you need to embed
  related rows, aggregate them in SQL with `ARRAY_AGG(STRUCT(...) LIMIT N)`.
- **Async everywhere I/O happens.** BigQuery paging via `asyncio.to_thread`,
  Cosmos via `azure-cosmos.aio`. Synchronous I/O in a pipeline blocks the
  whole runner.
- **Quality bar.** PR cannot merge until `ruff`, `pyright`, `pytest`, and
  `terraform validate` all pass locally and in CI.

## Adding a new pipeline

1. Create `py/apps/bq-cosmos-sync/src/bq_cosmos_sync/pipelines/<name>.py`
   subclassing `Pipeline`.
2. Set `name`, `container_name`, `partition_key_field`, `refresh_mode`,
   and (if incremental) `watermark_column`.
3. Implement `build_query(ctx)` — return SQL that does any JOINs and
   aggregations. Use `ctx.project_id`, `ctx.dataset`, and `ctx.watermark`.
4. Implement `row_to_document(row, *, ctx)` — pure projection, no I/O.
5. Register in `pipelines/registry.py::default_registry`.
6. Add a test in `tests/test_pipelines.py` (assert on SQL substrings and on
   document shape).
7. Update [docs/data-model.md](../docs/data-model.md) with the new container.

## Adding a new BigQuery source table

1. Update the schema in `notebooks/_build.py::SCHEMAS` and regenerate
   notebooks: `python3 notebooks/_build.py`.
2. Update the corresponding pipeline SQL to JOIN the new table.
3. Update [docs/data-model.md](../docs/data-model.md).
4. Reseed locally (run `notebooks/bigquery/02_seed_data.ipynb`) and rerun
   `03_validate.ipynb` to confirm the joins land cleanly.

## What not to touch without a very good reason

- `Pipeline` protocol in `pipelines/base.py` — extending it ripples to every
  pipeline.
- Cosmos partition-key choices in [docs/data-model.md](../docs/data-model.md)
  — changing a PK is a container-rebuild migration.
- Container App secret name format (no dots).
- `terraform window_duration = "P1D"` (not `"PT24H"`).

## Style

- **No inline justification comments.** Keep "why" in commit messages and PRs;
  code stays terse. The same rule applies to YAML / `.tfvars` / Dockerfile.
- **Type hints on every public function.** `pyright` runs in strict-ish mode.
- **Tests use real types, not Any.** Fakes live in `tests/fakes.py` and
  implement the same protocol the real client does.
- **Logging via `log_event(logger, event, /, *, level=..., **fields)`.** Never
  `logger.info(f"...")` — we want structured logs.

## Commands you'll use constantly

```bash
uv sync --project py/apps/bq-cosmos-sync

# run from inside each package so pyproject configs apply cleanly
(cd py/apps/bq-cosmos-sync && uv run ruff check src tests)
(cd py/apps/bq-cosmos-sync && uv run ruff format --check src tests)
(cd py/apps/bq-cosmos-sync && uv run pyright)
(cd py/apps/bq-cosmos-sync && uv run pytest -q)

(cd py/libs/bigquerykit && uv run pytest -q)
(cd py/libs/cosmosdbkit && uv run pytest -q)

cd infra && terraform fmt -recursive && terraform validate
```

## Recovering from "I broke the pipelines"

If you ever delete or corrupt the pipeline files, the data model is recorded
in [docs/data-model.md](../docs/data-model.md) and the canonical SQL is in
[docs/architecture.md](../docs/architecture.md). The five BigQuery source
table schemas live in `notebooks/_build.py::SCHEMAS`.
