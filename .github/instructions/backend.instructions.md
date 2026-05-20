---
description: Backend conventions for FastAPI, SSE, and storage abstractions.
applyTo: 'py/**'
---

# Backend Conventions

## Endpoint Patterns
- Define routes in `api/v1/` with `APIRouter(prefix="/api/v1")`.
- All request/response bodies use Pydantic models from `models/`.
- Keep route handlers thin — delegate logic to `services/` or `py/libs/`.
- Use `async def` for all handlers; never block the event loop.

## SSE Streaming Contract
Emit events as `event: {name}\ndata: {json}\n\n`:
1. `message_start` — `{"session_id": ..., "message_id": ...}`
2. `delta` — `{"token": ...}` (one per streamed token)
3. `tool_event` — `{"tool": ..., "status": ...}`
4. `done` — `{"ok": true}`

Format helper: `_sse(event, data)` in `api/v1/chat.py`. Use `StreamingResponse` with `media_type="text/event-stream"`.

## Storage Protocol
- All backends implement `Storage` protocol: `add_message()`, `list_messages()`.
- `InMemoryStorage`: default local dev (thread-safe `defaultdict`).
- `CosmosStorage`: production, uses parameterized queries to prevent injection.
- Factory: `get_storage()` selects based on `settings.storage_mode` env var.
- New backends: implement protocol → add branch in `get_storage()` → add config to `AppSettings`.

## FoundryClient & AgentManager
- `get_foundry_client()` returns a cached singleton — never instantiate `FoundryClient` directly.
- `AgentManager.temporary_agent()` context manager for ephemeral agents (auto-cleanup).
- `ToolRegistry.register()` decorator wraps tools with OpenTelemetry spans.

## Configuration
- `AppSettings` (extends `FoundrySettings`) loads from `.env` via Pydantic settings.
- Access via `get_settings()` (cached). Never hardcode endpoints, ports, or model names.

## Error Handling
- Let FastAPI handle validation errors (422) via Pydantic.
- Use `httpx` for external calls with explicit timeouts.
- Log errors with `structlog` from `core/logging.py`.

## Testing
- Tests live in `tests/` next to app code.
- `conftest.py` forces `STORAGE_MODE=inmemory` and clears settings cache.
- Use `httpx.AsyncClient` with `ASGITransport` for endpoint tests.
