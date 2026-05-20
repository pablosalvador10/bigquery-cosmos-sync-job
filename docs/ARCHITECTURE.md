# architecture

Cron-triggered batch sync. BigQuery is the source of truth, Cosmos is the
serving copy. Runs once a day, ships ~500 MB, exits.

```
                          ┌─ Private Endpoint ─► Cosmos DB (NoSQL, no shared keys)
BigQuery ──HTTPS via NAT─► Container App Job  ──┼─ Private Endpoint ─► Key Vault
                          │  (Python, async)    └─ Private Endpoint ─► Container Registry
                          │
                          └─► Log Analytics + App Insights
```

The vnet, NAT Gateway, NSGs, and Private Endpoints are part of the IaC
default — see [networking.md](networking.md). The single user-assigned
managed identity handles every Azure-side authentication — see
[identity.md](identity.md).

## How a run works

1. Read watermarks for each pipeline from `sync_metadata`.
2. For each pipeline:
   - `build_query()` returns the SQL (joins + aggregates live here).
   - Page rows via `google-cloud-bigquery`, wrapped in `asyncio.to_thread`.
   - `row_to_document()` projects each row into a Cosmos doc with id
     `<entity>::<source-pk>`.
   - `BatchWriter` upserts with bounded concurrency. Throttle responses
     retry with exponential backoff and respect `x-ms-retry-after-ms`.
   - Bad rows are isolated; the rest of the pipeline keeps going.
3. Write a `sync_metadata` summary doc with status, counts, watermark, and
   `run_id`. Watermark advances only to the last persisted row's timestamp.
4. Exit non-zero if any pipeline ended `failure`.

## Pipelines

Pipelines are stateless classes implementing a small protocol. The runner owns
batching, retries, error isolation, telemetry, and checkpointing so the
pipeline file is just SQL + projection.

```
build_query(ctx) -> str         # SQL string, may reference ctx.watermark
row_to_document(row, *, ctx) -> dict
extract_watermark(row) -> datetime | None   # default: row["updated_at"]
```

Register a new one in `pipelines/registry.py`. See
[extending.md](extending.md).

## Why these choices

- **Joins in BigQuery.** Columnar scan + `ARRAY_AGG(... LIMIT N)` for bounded
  embeds. Python stays a shipping layer. Cheaper than pulling N tables and
  joining in-memory once volumes grow.
- **Cosmos for NoSQL.** Point reads by partition key are the dominant access
  pattern; documents are denormalized so a serving query is one round-trip.
- **Container App Job, not Functions.** Job runs are minutes-long batches,
  not seconds. Scale-to-zero, managed identity, azd-native.
- **One row → one document.** Deterministic ids → re-runs are idempotent.
  No tombstones unless you need hard deletes; filter `deleted_at` in
  `build_query` and add a tombstone pipeline if so.

## Failure model

| Failure | Behaviour |
| --- | --- |
| One bad row (projection error) | counted in `rows_failed`, run continues |
| Cosmos 429 / 449 | retried with backoff, respects retry-after header |
| BigQuery 429 / quotaExceeded | retried by `bigquerykit.retry_on_rate_limit` |
| One pipeline fails | next pipeline still runs, job exits non-zero |
| Partial success | status `partial`, watermark advances to last persisted row |

## Scale notes

Sized for ~500 MB/day. Headroom paths when that grows:

- **More throughput** — bump per-container Cosmos RU/s, raise
  `BATCH_WRITER_CONCURRENCY`.
- **More pipelines** — run them in parallel by raising `SYNC_PARALLELISM`
  (semaphore in the runner). BQ slot quota is usually the next bottleneck.
- **Bigger pages** — raise `BQ_PAGE_SIZE`; memory grows linearly with page
  size × concurrency.
- **Beyond batch** — keep the pipeline classes, swap the cron for a Pub/Sub
  → Event Hubs bridge for sub-minute latency.
