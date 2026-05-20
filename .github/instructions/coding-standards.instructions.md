---
applyTo: "py/**/*.py"
---
# Python coding standards (repo-specific)

The general FDE rules live in `py_bestpractice.instructions.md`,
`py_models.instructions.md`, and `py_testing.instructions.md`. Read those
first. This file only captures the patterns that are specific to *this*
repo (BigQuery → Cosmos sync) and that aren't already covered by the
platform instructions.

## What the house rules already cover (don't restate, just follow)

- No `from __future__ import annotations`.
- No `__all__` — use redundant-alias re-exports (`from x import Y as Y`).
- No `print()` in app code — use `typer.echo(..., err=True)` or `log_event`.
- Pydantic `FrozenBaseModel` for value objects; pydantic `BaseModel` for
  domain models that are mutated in flight.
- Modern type syntax (`list[str]`, `X | None`); no `from typing import List`.
- One-line module + class + public-function docstring (PEP 257), no AI
  filler.
- `pytest-asyncio` with `asyncio_mode = "auto"`.

## Repo-specific exceptions

These are the only places we deliberately break the "no mutable container"
rule, and the reason is recorded here so reviewers don't have to ask:

- `BatchWriteResult` (`cosmos/writer.py`) — internal accumulator merged
  across concurrent upsert tasks. A frozen model would force a copy on
  every row.
- `QueryBuilder` (`bigquerykit`, `cosmosdbkit`) — fluent builder; `.bind()`
  mutates and returns `self`.
- `PipelineSummary` / `RunSummary` (`models.py`) — accumulated by the
  runner as a pipeline progresses, then logged at the end.

Everything else that holds a configuration snapshot (e.g. `PipelineContext`,
`Settings`) is a frozen pydantic model.

## Repo-specific patterns

### BigQuery paging
The sync wraps the sync BQ SDK with `asyncio.to_thread`. There's a known
asyncio bug where `StopIteration` raised inside `to_thread` becomes
`RuntimeError`. Use `_next_page(pages, sentinel)` in
`bigquerykit/dataset.py` — not `try / except StopIteration`.

### Cosmos batching
Always use `BatchWriter`. Don't call `upsert_item` in a loop — that's an
HTTP round-trip per row and you'll burn RUs.

### Watermark extraction
`Pipeline.extract_watermark` reads `updated_at` by default. Override it
if your pipeline projects a different column (the `learners` pipeline
does this for `effective_updated_at`).

### Structured logging
`log_event(logger, event, /, *, level=..., **fields)` from
`bq_cosmos_sync.logging`. First positional arg is a snake_case event name;
extra kwargs become JSON fields. No f-strings in log calls.

### Tests
- Fakes go in `tests/fakes.py` and implement the same protocol the real
  client does. No `MagicMock` for types we own.
- Sleep stubs use `async def _no_sleep(_: float) -> None: return None` —
  never a lambda that calls `asyncio.sleep(0)`, which recurses through
  the patched sleep.
