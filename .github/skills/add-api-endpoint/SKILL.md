---
name: add-api-endpoint
description: 'Guides adding a new FastAPI endpoint with Pydantic models, routing, and tests. Use when creating a new API route, adding a REST endpoint, or extending the backend API surface.'
argument-hint: 'Describe the endpoint purpose (e.g., "GET /api/v1/sessions to list sessions")'
---

## Purpose
Step-by-step workflow for adding a new FastAPI endpoint to `py/apps/app-template`.

## When to Use
- Adding a new REST endpoint (GET, POST, PUT, DELETE).
- Adding a new streaming SSE endpoint.
- Extending the `/api/v1/` route surface.

## Flow

1. **Define Pydantic models** in `py/apps/app-template/models/`:
   - Create request model (if POST/PUT) extending `BaseModel`.
   - Create response model extending `BaseModel`.
   - Follow patterns from `models/chat.py`: `Field(default_factory=...)` for UUIDs, timestamps.

2. **Create route file** in `py/apps/app-template/api/v1/`:
   - Create `{resource}.py` with `APIRouter(prefix="/api/v1", tags=["{resource}"])`.
   - Use `async def` for all handlers.
   - For streaming: return `StreamingResponse(generator(), media_type="text/event-stream")`.
   - Import and use `get_storage()` for persistence.

3. **Wire router** in `py/apps/app-template/main.py`:
   - Import the new router.
   - Add `app.include_router(router)` in the lifespan or module-level setup.

4. **Add tests** in `py/apps/app-template/tests/`:
   - Create `test_{resource}.py`.
   - Use `httpx.AsyncClient` with `ASGITransport(app=app)`.
   - Test success path, validation errors, and edge cases.
   - For streaming: verify SSE event names and JSON data.

5. **Update docs**:
   - Add endpoint to `docs/API.md`.

## Decision Logic
- **Sync endpoint**: Use when response is computed in one pass (< 1s).
- **Streaming endpoint**: Use when response is incremental (LLM tokens, long processing).
- **Both**: Provide sync for simple clients + streaming for UI (pattern from `chat.py`).

## Checklist
- [ ] Pydantic models defined with typed fields
- [ ] Route handler is `async def`
- [ ] Router wired in `main.py`
- [ ] Tests cover success and error paths
- [ ] API docs updated

## Next Action
After adding the endpoint, run `write-backend-tests` skill to ensure coverage.
