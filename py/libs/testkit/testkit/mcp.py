"""Fake MCP client for in-memory tool dispatch testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolCall:
    """A recorded MCP tool invocation."""

    tool: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class FakeMCPClient:
    """In-memory MCP server client for tests.

    Register tool handlers or canned responses, then dispatch
    tool calls and assert on the results.

    Usage::

        mcp = FakeMCPClient()
        mcp.register_tool("ping", lambda args: {"result": "pong"})
        result = await mcp.dispatch("ping", {"msg": "hello"})
        assert result["result"] == "pong"
        assert len(mcp.calls) == 1
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}
        self._canned: dict[str, dict[str, Any]] = {}
        self.calls: list[MCPToolCall] = []

    def register_tool(
        self,
        name: str,
        handler: Any | None = None,
        *,
        canned_result: dict[str, Any] | None = None,
    ) -> "FakeMCPClient":
        """Register a tool handler or canned result. Returns self for chaining."""
        if handler is not None:
            self._handlers[name] = handler
        elif canned_result is not None:
            self._canned[name] = canned_result
        return self

    async def dispatch(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch a tool call and return the result."""
        args = arguments or {}

        if tool in self._handlers:
            result = self._handlers[tool](args)
        elif tool in self._canned:
            result = self._canned[tool]
        else:
            result = {"tool": tool, "result": "not_implemented", "arguments": args}

        call = MCPToolCall(tool=tool, arguments=args, result=result)
        self.calls.append(call)
        return result

    def assert_tool_called(self, tool_name: str, *, times: int | None = None) -> None:
        """Assert a tool was called, optionally a specific number of times."""
        matching = [c for c in self.calls if c.tool == tool_name]
        assert matching, f"Tool '{tool_name}' was never called. Calls: {[c.tool for c in self.calls]}"
        if times is not None:
            assert len(matching) == times, (
                f"Expected '{tool_name}' called {times} times, got {len(matching)}"
            )

    def reset(self) -> None:
        """Clear all recorded calls."""
        self.calls.clear()
