# cosmosdbkit

Reusable async Azure Cosmos DB I/O toolkit shared across `py/` workspace.

Provides:

- `CosmosKitClient` — singleton-friendly wrapper around `azure.cosmos.aio.CosmosClient`
  with lazy connection, credential resolution, and lifecycle management.
- `CosmosContainer` — thin async wrapper exposing the operations actually used in
  this repo: `read_item`, `try_read_item`, `upsert_item`, `create_item`,
  `replace_item`, `delete_item`, `query`, `query_one`, `query_all`, `count`. It is
  structurally compatible with `ContainerProxy` from `py/apps/platform`.
- `QueryBuilder` — small helper that enforces parameterized SQL.
- `retry_on_throttle` — 429-aware async retry decorator.
- Typed errors (`NotFound`, `Conflict`, `Throttled`, `CosmosKitError`).

The kit is intentionally **domain-free**: no knowledge of submissions, judges,
participants, or any platform shape. Domain code lives in `py/apps/*` or other
libs and depends on this kit for I/O.
