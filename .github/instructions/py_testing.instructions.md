---
description: Python testing guidance for backend apps and reusable libs.
applyTo: '**/*test*.py,**/tests/**/*.py,**/py/**'
---

# Python Testing Guidelines

## Objectives
- Tests are executable documentation of durable behavior.
- Tests should pressure design toward clean seams and small modules.

## What To Test
- Public behavior, contracts, and observable outcomes.
- API request/response validation and SSE event contracts.
- Error paths that users or callers depend on.

## What Not To Test
- Incidental internals (private helper call order, implementation details).
- Duplicate scenarios with identical signal.

## Patterns
- Use arrange/act/assert structure.
- Prefer parametrized tests for related scenario sets.
- Prefer in-memory fakes for infra boundaries over deep mock chains.

## Quality Rules
- Keep tests readable and high-signal.
- Keep fixtures focused and explicit.
- Add regression tests for fixed bugs.
