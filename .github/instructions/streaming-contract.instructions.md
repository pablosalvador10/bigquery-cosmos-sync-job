---
description: SSE streaming contract between backend and frontend. Use when modifying streaming, events, real-time communication, or adding new event types.
applyTo: 'py/apps/**/api/**'
---

# Streaming Contract

## Event Sequence
Backend emits Server-Sent Events in this exact order:

```
event: message_start
data: {"session_id": "...", "message_id": "..."}

event: delta
data: {"token": "Hello"}

event: delta
data: {"token": " world"}

event: tool_event
data: {"tool": "summarize_text", "status": "completed"}

event: done
data: {"ok": true}
```

## Format
Each event is formatted as: `event: {name}\ndata: {json}\n\n`
Use the `_sse(event, data)` helper in `api/v1/chat.py`.

## Backend Emitter
- Located in `py/apps/app-template/api/v1/chat.py` → `_stream_reply()` async generator.
- Returns `StreamingResponse(..., media_type="text/event-stream")`.
- Must store messages via `Storage` before and after streaming.

## Frontend Parser
- Located in `ts/apps/ui-copilot-template/src/lib/api.ts` → `streamChat()`.
- Splits stream on `\n\n` boundaries, extracts `event:` and `data:` lines.
- `delta` events append tokens to current assistant message.
- `tool_event` events update the `ToolEvent` state.

## Adding a New Event Type
1. Define event name and JSON payload schema.
2. Add `yield _sse("new_event", {...})` in backend `_stream_reply()`.
3. Add parser branch in frontend `streamChat()`.
4. Add TypeScript type in `types.ts`.
5. Add state handling in `useStreamingChat` hook.
6. Update tests in `test_stream.py`.
