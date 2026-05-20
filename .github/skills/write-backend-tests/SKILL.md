---
name: write-backend-tests
description: 'Writes pytest tests for backend endpoints, services, and tools. Use when adding tests, writing test fixtures, testing API endpoints, testing streaming, or improving test coverage.'
argument-hint: 'Describe what to test (e.g., "new /api/v1/sessions endpoint", "custom storage backend")'
---

## Purpose
Step-by-step workflow for writing pytest tests for the FastAPI backend.

## When to Use
- Adding tests for a new endpoint.
- Testing a new storage backend or service.
- Testing tool functions.
- Improving test coverage.

## Flow

1. **Set up conftest.py** (if not present):
   - Located at `py/apps/app-template/tests/conftest.py`.
   - Forces `STORAGE_MODE=inmemory` so tests don't need Cosmos DB:
     ```python
     import pytest
     from core.config import get_settings

     @pytest.fixture(autouse=True)
     def force_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
         monkeypatch.setenv("STORAGE_MODE", "inmemory")
         get_settings.cache_clear()
     ```

2. **Write endpoint tests** — pattern from `test_api.py`:
   ```python
   import pytest
   from httpx import ASGITransport, AsyncClient
   from main import app

   @pytest.mark.asyncio
   async def test_my_endpoint():
       transport = ASGITransport(app=app)
       async with AsyncClient(transport=transport, base_url="http://test") as client:
           response = await client.post("/api/v1/my-endpoint", json={
               "field": "value"
           })
       assert response.status_code == 200
       data = response.json()
       assert "expected_field" in data
   ```

3. **Write streaming tests** — pattern from `test_stream.py`:
   ```python
   @pytest.mark.asyncio
   async def test_stream():
       transport = ASGITransport(app=app)
       async with AsyncClient(transport=transport, base_url="http://test") as client:
           response = await client.post("/api/v1/chat/stream", json={
               "message": "hello"
           })
       assert response.status_code == 200
       body = response.text
       assert "event: delta" in body
       assert "event: done" in body
   ```

4. **Write tool tests**:
   ```python
   import json
   from tools.my_tools import my_tool

   def test_my_tool():
       result = json.loads(my_tool("input"))
       assert "expected_key" in result
   ```

5. **Write storage tests**:
   ```python
   @pytest.mark.asyncio
   async def test_storage_roundtrip():
       storage = MyStorage()
       msg = StoredMessage(session_id="s1", role="user", content="hello")
       await storage.add_message(msg)
       messages = await storage.list_messages("s1")
       assert len(messages) == 1
       assert messages[0].content == "hello"
   ```

6. **Run tests**:
   ```bash
   cd py/apps/app-template
   uv run pytest tests/ -v
   ```

## Decision Logic
- **Endpoint test**: Use `httpx.AsyncClient` + `ASGITransport`. Test status codes and response shapes.
- **Unit test**: Call function directly. Test return values and edge cases.
- **Storage test**: Test round-trip (`add` → `list`), empty results, and session isolation.
- **Integration test**: Test full flow (request → storage → response) via endpoint.

## Checklist
- [ ] `conftest.py` forces inmemory storage
- [ ] Tests use `@pytest.mark.asyncio` for async
- [ ] Tests use `httpx.AsyncClient` (not `TestClient`) for async endpoints
- [ ] Success + error paths tested
- [ ] Streaming tests verify event names in body
- [ ] `uv run pytest tests/ -v` passes
