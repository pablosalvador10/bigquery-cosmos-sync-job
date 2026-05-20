---
name: test-infrastructure
description: 'Sets up test infrastructure using testkit shared fakes. Use when writing tests, creating test fixtures, setting up FakeCosmosContainer, FakeLLMClient, or testing SSE streams.'
argument-hint: 'Describe what you need to test (e.g., "chat endpoint with mocked LLM and Cosmos")'
---

## Purpose
Step-by-step guide for using testkit shared fakes and assertion helpers in tests.

## When to Use
- Writing unit tests for backend services.
- Testing API endpoints with mocked dependencies.
- Validating SSE streaming contract compliance.
- Setting up test fixtures in conftest.py.

## Available Fakes

| Fake | Purpose | Key Methods |
|------|---------|-------------|
| `FakeCosmosContainer` | In-memory Cosmos DB | `create_item`, `read_item`, `upsert_item`, `query_items`, `seed()` |
| `FakeLLMClient` | FIFO-seeded LLM responses | `seed_complete()`, `seed_stream()`, `complete()`, `stream()` |
| `FakeFoundryClient` | Foundry agent lifecycle | `agents_client.create_agent()`, `agents_client.delete_agent()` |
| `FakeAgentManager` | Agent create/run/cleanup | `temporary_agent()`, `run_agent()`, `set_run_response()` |
| `FakeStorage` | In-memory Storage protocol | `add_message()`, `list_messages()`, `assert_message_stored()` |
| `FakeMCPClient` | In-memory MCP dispatch | `register_tool()`, `dispatch()`, `assert_tool_called()` |

## Flow

1. **Set up fixtures** in `conftest.py`:
   ```python
   import pytest
   from testkit import FakeCosmosContainer, FakeLLMClient, FakeStorage

   @pytest.fixture
   def cosmos():
       container = FakeCosmosContainer(partition_key="/session_id")
       container.seed(
           {"id": "s1", "session_id": "s1", "status": "active"},
       )
       return container

   @pytest.fixture
   def llm():
       client = FakeLLMClient()
       client.seed_complete('{"action": "ANSWER", "confidence": 3}')
       return client

   @pytest.fixture
   def storage():
       return FakeStorage()
   ```

2. **Write async tests** (testkit supports both sync and async):
   ```python
   async def test_chat_stores_message(storage):
       from testkit.storage import StoredMessage

       msg = StoredMessage(session_id="s1", role="user", content="hello")
       await storage.add_message(msg)
       storage.assert_message_stored("s1", "user", "hello")
       storage.assert_session_has_messages("s1", 1)
   ```

3. **Test Cosmos DB patterns**:
   ```python
   from testkit import assert_cosmos_item

   async def test_upsert_and_query(cosmos):
       await cosmos.upsert_item({"id": "x", "session_id": "s1", "data": "test"})
       item = assert_cosmos_item(cosmos, "x", field_checks={"data": "test"})

       results = [r async for r in cosmos.query_items(
           "SELECT * FROM c WHERE c.session_id = @session_id",
           parameters=[{"name": "@session_id", "value": "s1"}],
       )]
       assert len(results) >= 1
   ```

4. **Test LLM interactions**:
   ```python
   async def test_agent_calls_llm(llm):
       llm.seed_complete("Paris is the capital of France")
       result = await llm.complete(
           messages=[{"role": "user", "content": "What is the capital of France?"}],
           model="gpt-4"
       )
       assert "Paris" in result
       assert llm.last_request.model == "gpt-4"
   ```

5. **Test SSE streaming**:
   ```python
   from testkit.sse import parse_sse_text, assert_sse_contract

   def test_sse_contract():
       sse_text = (
           'event: message_start\ndata: {"session_id": "s1"}\n\n'
           'event: delta\ndata: {"token": "hello"}\n\n'
           'event: done\ndata: {"ok": true}\n\n'
       )
       events = parse_sse_text(sse_text)
       assert_sse_contract(events)
   ```

6. **Test MCP tool dispatch**:
   ```python
   from testkit import FakeMCPClient, assert_tool_called

   async def test_mcp_dispatch():
       mcp = FakeMCPClient()
       mcp.register_tool("search", canned_result={"results": ["doc1", "doc2"]})
       result = await mcp.dispatch("search", {"query": "test"})
       assert result["results"] == ["doc1", "doc2"]
       assert_tool_called(mcp, "search", times=1)
   ```

## Assertion Helpers

| Helper | Purpose |
|--------|---------|
| `assert_cosmos_item(container, id, field_checks={})` | Assert item exists with field values |
| `assert_sse_sequence(events, ["start", "done"])` | Assert event type ordering |
| `assert_tool_called(mcp, "tool_name", times=N)` | Assert MCP tool was called |

## Checklist
- [ ] Fixtures set up in conftest.py using testkit fakes
- [ ] LLM responses seeded for deterministic tests
- [ ] Cosmos container seeded with test data
- [ ] SSE contract validated for streaming endpoints
- [ ] All async tests use `async def` with pytest-asyncio
