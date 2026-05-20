---
description: FastAPI endpoint, error handling, and response-contract conventions for Python services.
applyTo: '**/py/**'
---

# Python FastAPI Conventions

## Endpoint Design
- Use `APIRouter` under `api/v1/` and keep handler functions thin.
- Define request and response contracts with Pydantic models.
- Use `async def` handlers and non-blocking I/O.
- Push reusable orchestration into `services/` or shared libs in `py/libs`.

## Error Handling
- Let FastAPI/Pydantic handle validation failures naturally.
- Raise explicit HTTP/domain exceptions for known business failures.
- Do not catch broad exceptions only to re-raise them unchanged.
- Do not double-log and then raise; keep logs purposeful and structured.

## SSE Streaming
- Preserve SSE contract exactly for chat streaming:
  - `message_start`
  - `delta`
  - `tool_event`
  - `done`
- Emit JSON payloads and `text/event-stream` media type.
- Keep backend emitters and frontend parsers synchronized.

## Middleware And App Setup
- Configure CORS through settings, not hardcoded origins.
- Centralize telemetry and logging setup in app startup/lifespan.
- Add health endpoints for liveness/readiness probes.

## Dependency And Resource Management
- Reuse long-lived clients (Cosmos, Foundry, Service Bus) per process.
- Avoid creating heavyweight clients per request.
- For blocking SDK operations, isolate via executors.

## Testing Expectations
- Test endpoint behavior via public API contracts.
- Verify SSE framing and event sequence with integration-style tests.
- Prefer in-memory fakes/backends where possible.

## Anti-Patterns
- No route modules with heavy business logic.
- No direct `os.environ` access in handlers/services.
- No silent `except Exception: pass`.
- No mixing app-only logic into reusable library modules.
