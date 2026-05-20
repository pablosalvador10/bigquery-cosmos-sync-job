---
description: Testing conventions for Python backend and TypeScript frontend. Use when writing tests, fixtures, test configuration, or debugging test failures.
applyTo: '**/tests/**'
---

# Testing Conventions

## Python Backend Tests

### Location & Structure
- Tests at `py/apps/app-template/tests/`.
- Lib tests at `py/libs/{name}/tests/`.
- `conftest.py` forces `STORAGE_MODE=inmemory` and clears `get_settings` cache.

### Patterns
- Use `httpx.AsyncClient` with `ASGITransport(app=app)` for endpoint tests.
- Use `pytest.mark.asyncio` for async tests (with `pytest-asyncio`).
- Arrange/Act/Assert structure — test behavior, not internals.
- Prefer in-memory fakes over deep mocks at infrastructure boundaries.

### What to Test
- **Endpoints**: status codes, response shape (Pydantic model validation), error cases.
- **Streaming**: verify SSE event sequence (`delta`, `tool_event`, `done`) and parseable JSON data.
- **Storage**: `add_message` → `list_messages` round-trip for each backend.
- **Tools**: direct function call → verify JSON output shape.
- **Agent specs**: YAML loading → valid `AgentSpec` instance.

### Running
```bash
cd py/apps/app-template && uv run pytest tests/ -v
cd py/libs/foundrykit && uv run pytest tests/ -v
cd py/libs/agentkit && uv run pytest tests/ -v
```

## TypeScript Frontend Tests
- Lint: `pnpm --filter ui-copilot-template lint`
- Type check: `pnpm --filter ui-copilot-template typecheck`

## CI
- `lint-test.yml` workflow runs Python tests + linting on PR.
- `terraform-validate.yml` validates infrastructure.
