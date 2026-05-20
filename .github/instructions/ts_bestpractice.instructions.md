---
description: TypeScript and React best practices for this template repo.
applyTo: '**/ts/**'
---

# TypeScript / React Best Practices

## Baseline
- Use strict typing and explicit event/data contracts.
- Keep UI in components and non-UI logic in hooks/utils.

## Streaming UX
- Parse SSE events defensively and type the payloads.
- Keep frontend event names aligned with backend contract.
- Model loading, error, and reconnect states explicitly.

## Component Design
- Keep components focused and composable.
- Avoid hidden coupling to backend internals.
- Prefer clear props over global implicit state.

## Accessibility
- Use semantic HTML and labeled controls.
- Preserve keyboard and focus usability in chat flows.

## Performance
- Avoid unnecessary re-renders and expensive per-render work.
- Memoize only where measurable or clearly beneficial.
