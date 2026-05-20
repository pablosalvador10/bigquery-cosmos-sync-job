---
description: Python best practices for this template repo.
applyTo: '**/py/**'
---

# Python Best Practices

## Baseline
- Target Python 3.12+ syntax and typing quality.
- Use Pydantic models for request/response and durable domain contracts.
- Use `pydantic-settings` for configuration.

## Async And Concurrency
- Keep HTTP and I/O paths async.
- Never block event loop with long sync SDK calls.
- If SDK is blocking, use `loop.run_in_executor` explicitly.

## Architecture
- Keep app code in `py/apps` and reusable code in `py/libs`.
- Prefer `typing.Protocol` for swappable backends.
- Keep clients (Cosmos, Service Bus, Foundry, etc.) reused, not recreated per request.

## Logging And Errors
- Use structured logging from `core/logging.py`.
- Do not swallow exceptions silently.
- Raise explicit exceptions for recoverable contract failures.

## Docstrings
- Add module docstring for non-trivial modules.
- Add docstrings for public classes/functions explaining purpose and constraints.

## Imports And Dependencies
- Keep imports grouped and clean.
- Add dependencies only in the package you modify.
- Avoid adding new dependencies unless approved.
