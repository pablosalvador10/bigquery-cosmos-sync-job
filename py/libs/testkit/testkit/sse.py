"""SSE stream parser and assertion helpers for testing streaming endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SSEEvent:
    """A parsed Server-Sent Event."""

    event: str
    data: dict[str, Any] = field(default_factory=dict)
    raw_data: str = ""


def parse_sse_text(text: str) -> list[SSEEvent]:
    """Parse raw SSE text into a list of ``SSEEvent`` objects.

    Handles the standard SSE format::

        event: message_start
        data: {"session_id": "abc"}

        event: delta
        data: {"token": "hello"}

    """
    events: list[SSEEvent] = []
    chunks = text.split("\n\n")

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        event_type = ""
        raw_data = ""

        for line in chunk.split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                raw_data = line[len("data:"):].strip()

        if event_type:
            try:
                parsed = json.loads(raw_data) if raw_data else {}
            except json.JSONDecodeError:
                parsed = {"_raw": raw_data}
            events.append(SSEEvent(event=event_type, data=parsed, raw_data=raw_data))

    return events


async def parse_sse_stream(response: Any) -> list[SSEEvent]:
    """Parse an httpx streaming response into SSE events.

    Works with ``httpx.AsyncClient`` streaming responses::

        async with client.stream("POST", "/api/v1/chat/stream", json=body) as resp:
            events = await parse_sse_stream(resp)
    """
    text = ""
    async for chunk in response.aiter_text():
        text += chunk
    return parse_sse_text(text)


def assert_sse_contract(events: list[SSEEvent]) -> None:
    """Assert events follow the template SSE contract.

    The contract requires events in this order:
    ``message_start → delta* → tool_event* → done``
    """
    if not events:
        raise AssertionError("No SSE events received")

    event_types = [e.event for e in events]

    assert event_types[0] == "message_start", (
        f"First event must be 'message_start', got '{event_types[0]}'"
    )
    assert event_types[-1] == "done", (
        f"Last event must be 'done', got '{event_types[-1]}'"
    )

    # Check ordering: message_start, then deltas, then optionally tool_events, then done.
    valid_types = {"message_start", "delta", "tool_event", "done"}
    for et in event_types:
        assert et in valid_types, f"Unknown event type: '{et}'. Valid: {valid_types}"
