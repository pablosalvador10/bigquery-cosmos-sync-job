---
description: "Add a new FastAPI endpoint with Pydantic models, routing, and tests. Guided workflow from model definition to test verification."
---

# New API Endpoint

Help me add a new FastAPI endpoint to the backend.

## Steps

1. **Ask me** what the endpoint should do (method, path, input, output).

2. **Define Pydantic models** in `py/apps/app-template/models/`:
   - Request model (if POST/PUT)
   - Response model

3. **Create route** in `py/apps/app-template/api/v1/`:
   - `async def` handler
   - Use `APIRouter(prefix="/api/v1")`
   - Return typed response

4. **Wire router** in `main.py`:
   - Import and `app.include_router()`

5. **Write tests** in `py/apps/app-template/tests/`:
   - Test success path
   - Test validation errors
   - For streaming: verify SSE events

6. **Run tests**:
   ```bash
   cd py/apps/app-template && uv run pytest tests/ -v
   ```

7. **Update API docs** in `docs/API.md`.

8. **Show me** the complete endpoint, models, and tests.
