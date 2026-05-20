---
description: Frontend conventions for chat UX and SSE event handling.
applyTo: 'ts/**'
---

# Frontend Conventions

## Architecture
- React 19 + Vite + TypeScript.
- State logic lives in `hooks/` (e.g., `useStreamingChat`).
- UI components in `components/` — keep presentational, receive data via props.
- API layer in `lib/api.ts` — all backend communication here.
- Types in `types.ts` — typed `Message`, `ToolEvent`, and any new event types.

## SSE Streaming Contract
The `streamChat()` function in `lib/api.ts` parses SSE lines:
- `event: delta` + `data: {"token": "..."}` → append token to assistant message.
- `event: tool_event` + `data: {"tool": "...", "status": "..."}` → update `ToolEvent` state.
- `event: done` → stream complete.

When adding new event types:
1. Add type to `types.ts`.
2. Add parser branch in `streamChat()` (`lib/api.ts`).
3. Add state + handler in `useStreamingChat` hook.
4. Add display component in `components/`.

## Component Patterns
- `ToolCard`: renders tool execution status from `ToolEvent` — follow this pattern for new event cards.
- Keep components mobile-safe with responsive layouts.
- Handle loading/error/empty states explicitly.

## Development
- `pnpm --filter ui-copilot-template dev` — starts Vite dev server on `:5173`.
- `pnpm --filter ui-copilot-template build` — production build.
- `pnpm --filter ui-copilot-template lint` — ESLint checks.
