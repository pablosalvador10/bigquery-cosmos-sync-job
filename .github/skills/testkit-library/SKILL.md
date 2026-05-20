---
name: testkit-library
description: 'Reference for using and extending testkit — shared test fakes for Cosmos DB, LLM, Foundry, MCP, SSE, and storage. Use when writing tests, creating custom fakes, understanding assertion helpers, or extending testkit for new infrastructure.'
argument-hint: 'Describe what you need (e.g., "test agent that calls Cosmos and LLM", "add fake for Redis")'
---

## Purpose

Testkit provides **in-memory fakes and assertion helpers** for every infrastructure dependency in the template. It eliminates test infrastructure duplication — all apps and libs use the same fakes.

## Public API Summary

| Export | Type | Purpose |
|--------|------|---------|
| `FakeCosmosContainer` | Class | Dict-backed Cosmos DB with partition keys + ETags |
| `FakeLLMClient` | Class | FIFO-seeded LLM with request tracking |
| `FakeFoundryClient` | Class | Fake FoundryClient matching foundrykit interface |
| `FakeAgentManager` | Class | Fake AgentManager with lifecycle tracking |
| `FakeStorage` | Class | In-memory Storage protocol implementation |
| `FakeMCPClient` | Class | In-memory MCP tool dispatch |
| `SSEEvent` | Dataclass | Parsed SSE event |
| `parse_sse_stream` | Function | Parse raw SSE text → events |
| `assert_cosmos_item` | Function | Assert Cosmos item exists with field checks |
| `assert_sse_sequence` | Function | Assert SSE event ordering |
| `assert_tool_called` | Function | Assert MCP tool was called |

**Location:** `py/libs/testkit/testkit/`

## FakeCosmosContainer — Cosmos DB Fake

```python
from testkit import FakeCosmosContainer

container = FakeCosmosContainer(partition_key="/session_id")
```

### Methods:
| Method | Behavior |
|--------|----------|
| `create_item(body)` | Inserts item. Raises `ValueError` if ID exists. Adds `_etag`. |
| `read_item(item, partition_key)` | Returns item. Raises `KeyError` if missing. |
| `upsert_item(body)` | Insert or replace. Updates `_etag`. |
| `replace_item(item, body, headers={"If-Match": etag})` | Replace with ETag check. Raises on mismatch. |
| `delete_item(item, partition_key)` | Removes item. |
| `query_items(query, parameters)` | Parameter-based matching (not full SQL). |
| `seed(*items)` | Synchronous bulk insert for test setup. Returns self. |
| `all_items` | Property — list of all stored items. |
| `len(container)` | Number of items. |

### Usage:
```python
# Setup
container = FakeCosmosContainer(partition_key="/session_id")
container.seed(
    {"id": "1", "session_id": "s1", "role": "user", "content": "hello"},
    {"id": "2", "session_id": "s1", "role": "assistant", "content": "hi"},
)

# CRUD
item = await container.create_item({"id": "3", "session_id": "s2", "data": "new"})
result = await container.read_item("3", partition_key="s2")
await container.upsert_item({"id": "3", "session_id": "s2", "data": "updated"})

# Query with parameters
results = []
async for item in container.query_items(
    "SELECT * FROM c WHERE c.session_id = @sid",
    parameters=[{"name": "@sid", "value": "s1"}],
):
    results.append(item)

# ETag-based optimistic concurrency
created = await container.create_item({"id": "x", "session_id": "s1"})
await container.replace_item("x",
    {"id": "x", "session_id": "s1", "updated": True},
    headers={"If-Match": created["_etag"]}
)
```

## FakeLLMClient — LLM Fake

```python
from testkit import FakeLLMClient

llm = FakeLLMClient(fallback="default response")
```

### Seeding responses (FIFO queue):
```python
llm.seed_complete("First response")
llm.seed_complete("Second response")
llm.seed_stream(["chunk1 ", "chunk2 ", "chunk3"])

# Responses are consumed in order
r1 = await llm.complete(messages=[...])  # "First response"
r2 = await llm.complete(messages=[...])  # "Second response"
r3 = await llm.complete(messages=[...])  # "default response" (queue empty)
```

### Streaming:
```python
llm.seed_stream(["Hello ", "world!"])
async for chunk in llm.stream(messages=[...]):
    print(chunk.text)  # "Hello ", "world!"
```

### Request tracking:
```python
await llm.complete(messages=[{"role": "user", "content": "test"}], model="gpt-4")
assert len(llm.requests) == 1
assert llm.last_request.model == "gpt-4"
assert llm.last_request.messages[0]["content"] == "test"
```

### Reset:
```python
llm.reset()  # Clear queue + recorded requests
```

## FakeFoundryClient + FakeAgentManager

```python
from testkit import FakeFoundryClient, FakeAgentManager

# Test Foundry agent lifecycle
client = FakeFoundryClient()
agent = client.agents_client.create_agent(name="test", model="gpt-4")
assert len(client.agents_client.created) == 1
client.agents_client.delete_agent(agent.id)
assert agent.id in client.agents_client.deleted

# Test AgentManager patterns
manager = FakeAgentManager()
manager.set_run_response("custom answer")

with manager.temporary_agent(name="ephemeral", model="gpt-4") as agent:
    assert agent.name == "ephemeral"
    result = manager.run_agent(agent.id, "thread-1")
    assert result.content == "custom answer"

assert len(manager.created_agents) == 1
assert len(manager.deleted_agents) == 1  # Auto-cleaned up
```

## FakeStorage — Storage Protocol Fake

```python
from testkit import FakeStorage
from testkit.storage import StoredMessage

storage = FakeStorage()

# Add messages
msg = StoredMessage(session_id="s1", role="user", content="hello")
await storage.add_message(msg)

# Query
messages = await storage.list_messages("s1")
assert len(messages) == 1

# Assertions
storage.assert_message_stored("s1", "user", "hello")
storage.assert_session_has_messages("s1", 1)

# Inspect all
print(storage.all_messages)  # List of all messages across sessions

# Reset
storage.reset()
```

## FakeMCPClient — MCP Tool Dispatch Fake

```python
from testkit import FakeMCPClient

mcp = FakeMCPClient()

# Register with handler function
mcp.register_tool("search", handler=lambda args: {"results": ["doc1", "doc2"]})

# Register with canned result
mcp.register_tool("ping", canned_result={"result": "pong"})

# Dispatch
result = await mcp.dispatch("search", {"query": "test"})
assert result["results"] == ["doc1", "doc2"]

# Assertions
mcp.assert_tool_called("search", times=1)
print(mcp.calls)  # List of MCPToolCall objects
```

## SSE Testing Helpers

```python
from testkit.sse import parse_sse_text, assert_sse_contract, SSEEvent
from testkit import assert_sse_sequence

# Parse raw SSE text
text = 'event: message_start\ndata: {"session_id": "s1"}\n\nevent: delta\ndata: {"token": "hi"}\n\nevent: done\ndata: {"ok": true}\n\n'
events = parse_sse_text(text)
assert events[0].event == "message_start"
assert events[0].data["session_id"] == "s1"

# Full contract validation (message_start required first, done required last)
assert_sse_contract(events)  # Raises AssertionError if invalid

# Sequence checking (order matters, gaps allowed)
assert_sse_sequence(events, ["message_start", "done"])
```

## Assertion Helpers

| Helper | Purpose | Raises |
|--------|---------|--------|
| `assert_cosmos_item(container, id, field_checks={})` | Item exists + field values match | `AssertionError` |
| `assert_sse_sequence(events, expected_types)` | Event types appear in order | `AssertionError` |
| `assert_tool_called(mcp, tool_name, times=N)` | MCP tool was called N times | `AssertionError` |

## Extension — Adding a New Fake

When adding a new infrastructure dependency (e.g., Redis, Blob Storage):

1. **Create the fake** in `testkit/{name}.py`:
```python
# testkit/redis.py
class FakeRedisClient:
    """In-memory Redis fake for testing."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def seed(self, **items: str) -> "FakeRedisClient":
        self._store.update(items)
        return self
```

2. **Export from `__init__.py`**:
```python
from .redis import FakeRedisClient as FakeRedisClient
```

3. **Add assertion helper** (if useful) to `assertions.py`:
```python
def assert_redis_key(client: FakeRedisClient, key: str, expected: str) -> None:
    import asyncio
    value = asyncio.get_event_loop().run_until_complete(client.get(key))
    assert value == expected, f"Key '{key}': expected '{expected}', got '{value}'"
```

4. **Write tests** in `testkit/tests/test_redis.py`.

## Conftest Patterns

Standard fixture setup for any app:

```python
# tests/conftest.py
import pytest
from testkit import FakeCosmosContainer, FakeLLMClient, FakeStorage, FakeMCPClient

@pytest.fixture
def cosmos():
    return FakeCosmosContainer(partition_key="/session_id")

@pytest.fixture
def llm():
    return FakeLLMClient()

@pytest.fixture
def storage():
    return FakeStorage()

@pytest.fixture
def mcp():
    return FakeMCPClient()
```

## File Map

| File | Contains |
|------|----------|
| `cosmos.py` | `FakeCosmosContainer` |
| `llm.py` | `FakeLLMClient`, `LLMRequest`, `StreamChunk` |
| `foundry.py` | `FakeFoundryClient`, `FakeAgentManager`, `FakeAgent`, `FakeRunResult` |
| `storage.py` | `FakeStorage`, `StoredMessage` |
| `mcp.py` | `FakeMCPClient`, `MCPToolCall` |
| `sse.py` | `SSEEvent`, `parse_sse_stream`, `parse_sse_text`, `assert_sse_contract` |
| `assertions.py` | `assert_cosmos_item`, `assert_sse_sequence`, `assert_tool_called` |

## Checklist
- [ ] Using testkit fakes instead of mocking with `unittest.mock`
- [ ] LLM responses seeded for deterministic tests
- [ ] Cosmos container seeded with `seed()` for setup
- [ ] SSE contract validated for streaming endpoints
- [ ] All async tests use `async def` with `asyncio_mode = "auto"`
- [ ] Custom fakes follow testkit patterns (sync `seed()`, async operations)
