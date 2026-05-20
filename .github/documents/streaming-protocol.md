# SSE Streaming Protocol Reference

## Overview
The backend emits Server-Sent Events (SSE) over HTTP POST to `/api/v1/chat/stream`. The frontend parses these events to build the chat UI incrementally.

## HTTP Contract

**Request:**
```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "session_id": "uuid-string",
  "message_id": "uuid-string",
  "message": "user input text",
  "history": []
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
```

## Event Sequence

Events are emitted in this exact order:

### 1. `message_start`
Signals the beginning of a new assistant message.
```
event: message_start
data: {"session_id": "abc-123", "message_id": "def-456"}
```

### 2. `delta` (repeated)
Streamed tokens, one per event. Append to current message.
```
event: delta
data: {"token": "Hello"}

event: delta
data: {"token": " world,"}

event: delta
data: {"token": " how"}
```

### 3. `tool_event` (zero or more)
Tool execution status updates.
```
event: tool_event
data: {"tool": "summarize_text", "status": "completed"}
```

Possible `status` values:
- `started` — tool execution began
- `completed` — tool returned successfully
- `failed` — tool threw an error

### 4. `done`
Signals stream completion.
```
event: done
data: {"ok": true}
```

## SSE Format
Each event follows the SSE spec:
```
event: {event_name}\n
data: {json_payload}\n
\n
```

Two newlines (`\n\n`) separate events. The `_sse()` helper in `api/v1/chat.py` formats this:
```python
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
```

## Frontend Parsing
The `streamChat()` function in `lib/api.ts`:
1. Reads the response body as a stream.
2. Splits on `\n\n` boundaries.
3. Extracts `event:` and `data:` lines.
4. Routes to callbacks based on event name.

## Adding Custom Events
1. Choose an event name (lowercase, no spaces).
2. Define the JSON payload shape.
3. Backend: yield `_sse("my_event", {...})` in the stream generator.
4. Frontend: add parser branch + callback in `streamChat()`.
5. Update types in `types.ts`.
6. Add tests verifying the event appears in stream output.
