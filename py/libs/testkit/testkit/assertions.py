"""Assertion helpers for common test patterns."""

from __future__ import annotations

from typing import Any

from .cosmos import FakeCosmosContainer
from .mcp import FakeMCPClient
from .sse import SSEEvent


def assert_cosmos_item(
    container: FakeCosmosContainer,
    item_id: str,
    *,
    partition_key: str | None = None,
    field_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assert an item exists in the container and optionally check fields.

    Returns the matched item for further assertions.
    """
    items = container.all_items
    matches = [i for i in items if i.get("id") == item_id]
    assert matches, f"Item '{item_id}' not found. Items: {[i.get('id') for i in items]}"

    item = matches[0]
    if field_checks:
        for field_name, expected in field_checks.items():
            actual = item.get(field_name)
            assert actual == expected, (
                f"Field '{field_name}': expected {expected!r}, got {actual!r}"
            )
    return item


def assert_sse_sequence(
    events: list[SSEEvent],
    expected_types: list[str],
) -> None:
    """Assert that event types appear in the expected order.

    Does NOT require exact match — only checks that the listed types
    appear in the given sequence (other events may appear between them).
    """
    actual_types = [e.event for e in events]
    idx = 0
    for expected in expected_types:
        while idx < len(actual_types) and actual_types[idx] != expected:
            idx += 1
        assert idx < len(actual_types), (
            f"Expected event '{expected}' not found after position {idx}. "
            f"Actual: {actual_types}"
        )
        idx += 1


def assert_tool_called(
    mcp: FakeMCPClient,
    tool_name: str,
    *,
    times: int | None = None,
    argument_checks: dict[str, Any] | None = None,
) -> None:
    """Assert a tool was called on the MCP client, optionally with argument checks."""
    mcp.assert_tool_called(tool_name, times=times)
    if argument_checks:
        matching = [c for c in mcp.calls if c.tool == tool_name]
        for call in matching:
            for key, expected in argument_checks.items():
                actual = call.arguments.get(key)
                assert actual == expected, (
                    f"Tool '{tool_name}' arg '{key}': expected {expected!r}, got {actual!r}"
                )
