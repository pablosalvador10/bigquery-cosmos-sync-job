"""Tests for SSE parsing and assertion helpers."""

import pytest

from testkit.sse import SSEEvent, parse_sse_text, assert_sse_contract
from testkit import assert_sse_sequence


class TestParseSSEText:
    def test_parses_events(self):
        text = (
            "event: message_start\ndata: {\"session_id\": \"s1\"}\n\n"
            "event: delta\ndata: {\"token\": \"hi\"}\n\n"
            "event: done\ndata: {\"ok\": true}\n\n"
        )
        events = parse_sse_text(text)
        assert len(events) == 3
        assert events[0].event == "message_start"
        assert events[0].data["session_id"] == "s1"
        assert events[1].event == "delta"
        assert events[2].event == "done"

    def test_empty_text(self):
        assert parse_sse_text("") == []

    def test_malformed_json(self):
        text = "event: delta\ndata: not-json\n\n"
        events = parse_sse_text(text)
        assert events[0].data == {"_raw": "not-json"}


class TestSSEContract:
    def test_valid_contract(self):
        events = [
            SSEEvent(event="message_start"),
            SSEEvent(event="delta"),
            SSEEvent(event="delta"),
            SSEEvent(event="tool_event"),
            SSEEvent(event="done"),
        ]
        assert_sse_contract(events)  # Should not raise

    def test_missing_start(self):
        events = [SSEEvent(event="delta"), SSEEvent(event="done")]
        with pytest.raises(AssertionError, match="message_start"):
            assert_sse_contract(events)

    def test_missing_done(self):
        events = [SSEEvent(event="message_start"), SSEEvent(event="delta")]
        with pytest.raises(AssertionError, match="done"):
            assert_sse_contract(events)

    def test_empty_events(self):
        with pytest.raises(AssertionError, match="No SSE events"):
            assert_sse_contract([])


class TestAssertSSESequence:
    def test_sequence_matches(self):
        events = [
            SSEEvent(event="message_start"),
            SSEEvent(event="delta"),
            SSEEvent(event="done"),
        ]
        assert_sse_sequence(events, ["message_start", "done"])

    def test_sequence_fails(self):
        events = [
            SSEEvent(event="done"),
            SSEEvent(event="message_start"),
        ]
        with pytest.raises(AssertionError, match="not found"):
            assert_sse_sequence(events, ["message_start", "done", "extra"])
