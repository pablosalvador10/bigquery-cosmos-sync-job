"""Tests for SSE streaming endpoint event contract."""

from fastapi.testclient import TestClient

from main import app


def test_stream_emits_all_sse_events() -> None:
    """Verify the full SSE event sequence: message_start, delta, tool_event, done."""
    client = TestClient(app)
    payload = {"message": "stream this please"}

    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        body = "".join(
            [chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_raw()]
        )

    assert response.status_code == 200
    assert "event: message_start" in body
    assert "event: delta" in body
    assert "event: tool_event" in body
    assert "event: done" in body
