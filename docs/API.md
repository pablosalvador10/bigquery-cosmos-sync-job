# API

## `GET /healthz`
Returns service liveness.

## `POST /api/v1/chat`
Request:
```json
{ "session_id": "optional", "message": "hello" }
```

Response:
```json
{ "session_id": "...", "message_id": "...", "response": "..." }
```

## `POST /api/v1/chat/stream`
Server-Sent Events stream.

Events:
- `message_start`
- `delta`
- `tool_event`
- `done`
