# troubleshooting

The things you'll actually hit.

## Job exits non-zero but logs say success

The runner exits non-zero if **any** pipeline ended `failure`. Partials count
as success at the job level.

```sql
SELECT TOP 5 * FROM c WHERE c.status = 'failure' ORDER BY c.finished_at DESC
```

## Cosmos 429 (RU throttling)

The writer already retries with backoff. Persistent 429s = underprovisioned.

```bash
az cosmosdb sql container throughput update \
  --account-name <acc> --database-name learnsphere \
  --name learners --throughput 1000
```

A full seed run should stay well under 100 RU/s. If you're burning more,
check your custom pipelines for cross-partition queries — the runner only
does upserts.

## BigQuery 403 quotaExceeded / rateLimitExceeded

`bigquerykit.retry_on_rate_limit` handles transient cases. Persistent
failures usually mean concurrent-query quota. Default `SYNC_PARALLELISM=1`
already runs pipelines sequentially.

## Containers stay empty after a run

In order of likelihood:

1. `--dry-run` flag or `SYNC_DRY_RUN=true`.
2. BigQuery returned zero rows. Run `bigquery/03_validate.ipynb`.
3. Wrong `COSMOS_DATABASE`. Check with `az cosmosdb sql database show`.

## Watermark doesn't advance

For `full` pipelines this is expected. For `learners`: check the latest
`sync_metadata` doc — if `watermark` is null, both `learners.updated_at` and
all `enrollments.last_activity_at` are null. Fix the source.

## ImportError after a workspace change

```bash
uv sync --project py/apps/bq-cosmos-sync
```

## `secret not found: gcp-sa-json` on first deploy

`postprovision` didn't run, or `GCP_SA_JSON_PATH` wasn't set.

```bash
azd env set GCP_SA_JSON_PATH ./secrets/gcp-sa.json
azd provision
```

## `Container App secret name 'gcp-sa.json' is invalid`

Dots aren't allowed in Container App secret names. Use `gcp-sa-json`. The
image mounts it at `/secrets/gcp-sa-json`.

## Terraform: `window_duration must be P...`

Use `P1D`, not `PT24H`. The v2 scheduled query rules resource is strict.

## Local emulator: SSL cert verification failed

```bash
export COSMOS_EMULATOR=true
```

Dev only. Never set in Azure.
