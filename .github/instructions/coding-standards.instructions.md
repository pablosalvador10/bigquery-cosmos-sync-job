---
description: Coding standards for Python, FastAPI, SSE streaming, TypeScript UI, and Terraform in this template repo.
applyTo: '**'
---

# Coding Standards

## General
- Keep code simple, typed, and readable.
- Reuse existing modules before creating new ones.
- Keep edits minimal and scoped to the task.
- Never commit secrets, credentials, or keys.
- Add module-level and public API docstrings in Python.

## Python / FastAPI
- Use `async` handlers and non-blocking I/O for API paths.
- Validate request/response with Pydantic models.
- Keep route handlers thin; move reusable logic to services/libs.
- Use structured logging and tracing hooks from `core/`.
- Use `pydantic-settings` for configuration, not direct `os.environ` reads.
- Prefer protocol-first abstractions (`typing.Protocol`) for replaceable backends.
- Keep Azure clients singleton-like and reused per process where possible.
- Avoid blocking SDK calls in event loop; use executor when needed.

## SSE Contract
- Preserve these event names exactly:
  - `message_start`
  - `delta`
  - `tool_event`
  - `done`
- Emit JSON payloads for each event.
- Keep frontend parser and backend emitter in sync.

## TypeScript / React
- Keep state logic in hooks and UI in components.
- Use explicit types for API payloads and stream events.
- Avoid hidden coupling to backend internals.
- Keep mobile-safe layouts and clear UX states (loading/error/empty).

## Infrastructure
- Prefer variable-driven Terraform modules.
- Do not hardcode tenant/subscription/resource IDs.
- Keep outputs aligned with runtime configuration and docs.

## Dependencies
- Do not add new dependencies without explicit approval.
- If required, add only at the package scope you modify.

## Testing and Verification
- Add or update tests for behavior changes.
- Validate API, SSE, and parsing behavior together.
- Run lint/validate checks before completion.
- Use clear arrange/act/assert tests that encode behavior, not internals.
- Prefer in-memory fakes over brittle deep mocks for infrastructure boundaries.

## Anti-Patterns
- No unnecessary wrapper/facade/manager layers.
- No broad refactors for a narrow fix.
- No duplicate utility logic when a shared module exists.
- No silent `except Exception: pass`.
- No `print()` in app/library runtime paths.
- No direct library-to-app coupling across template boundaries.
