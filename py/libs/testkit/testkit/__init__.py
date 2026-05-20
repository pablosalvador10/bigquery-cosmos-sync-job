"""testkit — Shared test utilities and fakes for the agentic app template.

Provides in-memory fakes for Cosmos DB, LLM clients, Foundry agents,
storage backends, MCP servers, and SSE stream testing. Designed to
eliminate test infrastructure duplication across template apps.

Usage::

    from testkit import FakeCosmosContainer, FakeLLMClient, FakeStorage

    container = FakeCosmosContainer(partition_key="/session_id")
    llm = FakeLLMClient()
    llm.seed_complete("Hello from the agent")
    storage = FakeStorage()
"""

from .assertions import (
    assert_cosmos_item as assert_cosmos_item,
    assert_sse_sequence as assert_sse_sequence,
    assert_tool_called as assert_tool_called,
)
from .cosmos import FakeCosmosContainer as FakeCosmosContainer
from .foundry import FakeAgentManager as FakeAgentManager, FakeFoundryClient as FakeFoundryClient
from .llm import FakeLLMClient as FakeLLMClient
from .mcp import FakeMCPClient as FakeMCPClient
from .sse import SSEEvent as SSEEvent, parse_sse_stream as parse_sse_stream
from .storage import FakeStorage as FakeStorage
