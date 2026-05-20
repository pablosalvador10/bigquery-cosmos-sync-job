# extending

How to add things without breaking the contract.

## A new pipeline

1. Subclass `Pipeline` in `py/apps/bq-cosmos-sync/src/bq_cosmos_sync/pipelines/<name>.py`.
2. Set `name`, `container_name`, `partition_key_field`, `refresh_mode`, and
   `watermark_column` if incremental.
3. Implement `build_query(ctx)` — SQL string. Use `ctx.project_id`,
   `ctx.dataset`, `ctx.watermark` (None on first run / full refresh).
4. Implement `row_to_document(row, *, ctx)` — pure projection.
5. Register in `pipelines/registry.py::default_registry`.
6. Add a test in `tests/test_pipelines.py`. Assert on SQL substrings and on
   document shape.
7. Update [data-model.md](data-model.md).

## A new BigQuery source table

1. Update `notebooks/_build.py::SCHEMAS`, then `python3 notebooks/_build.py`.
2. JOIN the new table in the relevant pipeline SQL.
3. Update [data-model.md](data-model.md).
4. Reseed (`bigquery/02_seed_data.ipynb`) and revalidate
   (`bigquery/03_validate.ipynb`).

## A new container partition key

This is a rebuild, not a migration. Cosmos doesn't let you change a PK in
place. Create a new container with the new PK, run a one-off backfill, swap
the pipeline's `partition_key_field`, drop the old container.

## A new alert

Add a `azurerm_monitor_scheduled_query_rules_alert_v2` block in
[`infra/main.tf`](../infra/main.tf). Reuse the existing action group. Keep
`window_duration = "P1D"`.

## Don't touch without good reason

- `Pipeline` protocol in `pipelines/base.py` — changes ripple to every pipeline.
- PKs in [data-model.md](data-model.md) — see above.
- Container App secret name format — no dots.
