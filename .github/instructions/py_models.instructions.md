---
description: Pydantic modeling conventions for Python apps and libraries in this template.
applyTo: '**/py/**'
---

# Python Models (Pydantic)

## Purpose
Use Pydantic models as the default contract type for API payloads, domain entities, tool inputs/outputs, and persisted documents.

## Core Rules
- Prefer `BaseModel` for structured data; avoid ad-hoc dict contracts.
- Add explicit field types and defaults; avoid implicit optional behavior.
- Use `Field(...)` for constraints (length, patterns, bounds) where applicable.
- Keep model names domain-meaningful (`ChatRequest`, `StoredMessage`, etc.).
- Add concise docstrings for public models that capture intent and constraints.

## Nullability
- Use `x: str` for required non-null values.
- Use `x: str | None` for required nullable values.
- Use `x: str | None = None` for optional nullable values.
- Do not use empty strings, zero, or `False` as missing-value sentinels when `None` is the intended state.

## API Model Boundaries
- Keep API request/response models separate from persistence/internal models when concerns diverge.
- Do not leak internal-only fields (partition keys, diagnostics, private metadata) to API responses.
- Convert at boundaries (service -> API model), not deep inside infrastructure code.

## Persistence Models
- For Cosmos documents, include stable identifiers and partition key fields explicitly.
- Keep timestamp fields ISO-8601 UTC strings or strongly typed datetime fields with clear serialization behavior.
- Prefer additive schema evolution to avoid breaking existing persisted records.

## Validation And Serialization
- Use model validation methods to normalize/validate external inputs.
- Keep JSON payload contracts stable and explicit when used by frontend or tools.
- Avoid custom serialization unless required; document any non-default behavior.

## Anti-Patterns
- No giant “kitchen sink” models with mixed responsibilities.
- No untyped `dict`/`Any` payloads where a model contract is feasible.
- No business logic in models beyond lightweight validation/normalization.
