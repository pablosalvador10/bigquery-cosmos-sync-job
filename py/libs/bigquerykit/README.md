# bigquerykit

Reusable async Google BigQuery I/O toolkit shared across the `py/` workspace.

Mirrors [`ms-fde-cosmosdbkit`](../cosmosdbkit) so applications that move data
between BigQuery and Cosmos DB get a uniform mental model on both sides.

Provides:

- `BigQueryKitClient` — singleton-friendly wrapper around `google.cloud.bigquery.Client`
  with lazy connection, credential resolution, and lifecycle management. The
  underlying SDK is synchronous; the kit wraps blocking calls behind
  `asyncio.to_thread` so callers in async apps get a uniform interface.
- `BigQueryDataset` — async wrapper exposing the operations actually used in
  this repo: `query_rows`, `query_one`, `query_all`, `count`, `exists_table`,
  `create_table`, `insert_rows`, plus a `table_ref()` helper.
- `QueryBuilder` — small helper that enforces parameterized SQL with named
  placeholders (`@name`) and validates value types.
- `retry_on_rate_limit` — async retry decorator that backs off on rate-limit
  or quota errors.
- Typed errors (`NotFound`, `PermissionDenied`, `RateLimited`, `BadRequest`,
  `BigQueryKitError`).

The kit is intentionally **domain-free**: no knowledge of LearnSphere,
learners, or sync pipelines. Domain code lives in `py/apps/*` and depends on
this kit for I/O.

## Quick example

```python
import asyncio

from ms.fde.bigquerykit import BigQueryKitClient, QueryBuilder


async def main() -> None:
    async with BigQueryKitClient(project="my-gcp-project") as bq:
        ds = bq.get_dataset("learnsphere")

        # Parameterized query
        sql, params = (
            QueryBuilder(f"SELECT * FROM `{ds.table_ref('learners')}` "
                         f"WHERE country = @country LIMIT 10")
            .bind("country", "US")
            .build()
        )
        async for page in ds.query_rows(sql, parameters=params, page_size=500):
            for row in page:
                print(row)


asyncio.run(main())
```

## Credentials

`BigQueryKitClient` accepts credentials in three ways:

1. `credentials_path=` — path to a service-account JSON key.
2. `credentials_info=` — already-parsed service-account JSON as a dict.
3. Neither — falls back to Application Default Credentials
   (`GOOGLE_APPLICATION_CREDENTIALS` env var, workload identity, gcloud login).

Tests can inject a fake by passing `client_factory=lambda project, creds, loc: FakeClient()`.
