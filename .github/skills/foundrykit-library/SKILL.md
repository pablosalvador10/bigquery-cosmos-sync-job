---
name: foundrykit-library
description: 'Reference for using and extending foundrykit — Azure AI Foundry client, AgentManager, ToolRegistry, and FoundrySettings. Use when working with Azure AI credentials, creating/running agents, registering tools, or extending foundrykit for custom needs.'
argument-hint: 'Describe what you need (e.g., "add custom credential provider", "stream agent with tool calls")'
---

## Purpose

Foundrykit is the **runtime layer** for Azure AI Foundry agents. It handles credentials, agent lifecycle, tool registration, and OpenTelemetry tracing. This skill covers every public class, method, and extension point.

## Public API Summary

| Export | Type | Purpose |
|--------|------|---------|
| `FoundrySettings` | Pydantic `BaseSettings` | Environment-based config (endpoint, model, credentials) |
| `FoundryClient` | Class | Singleton wrapper around Azure `AgentsClient` |
| `get_foundry_client()` | Factory | Returns cached `FoundryClient` singleton |
| `AgentManager` | Class | Agent lifecycle: create, run, stream, auto-cleanup |
| `AgentStreamEvent` | Dataclass | Typed event from streaming agent runs |
| `ToolRegistry` | Class | Decorator-based tool collector with OTel tracing |

**Location:** `py/libs/foundrykit/foundrykit/`

## FoundrySettings — Configuration

```python
from foundrykit import FoundrySettings

class FoundrySettings(BaseSettings):
    foundry_project_endpoint: str = ""     # Azure AI Foundry project URL
    foundry_model: str = "gpt-4.1-mini"    # Default deployment name
    foundry_credential_mode: Literal["dev", "managed_identity"] = "dev"
    azure_client_id: str | None = None     # For managed identity
```

- Loads from `.env` automatically.
- `dev` mode → `DefaultAzureCredential` (uses `az login`).
- `managed_identity` mode → `ManagedIdentityCredential` with `azure_client_id`.
- **Extend** by subclassing: `class AppSettings(FoundrySettings): ...` (see app-template's `core/config.py`).

## FoundryClient — Singleton Azure Connection

```python
from foundrykit import get_foundry_client

client = get_foundry_client()          # Cached singleton — ALWAYS use this
agents_client = client.agents_client   # Lazy-initialized Azure AgentsClient
```

**Rules:**
- Never call `FoundryClient()` directly — use `get_foundry_client()`.
- The `agents_client` property is lazy: first access creates the connection.
- One instance per process. Thread-safe due to `@lru_cache(maxsize=1)`.

**Extension — Custom credential provider:**
```python
from foundrykit.client import FoundryClient

class MyClient(FoundryClient):
    def _build_credential(self):
        # Return any TokenCredential implementation
        from azure.identity import EnvironmentCredential
        return EnvironmentCredential()
```

## AgentManager — Agent Lifecycle

```python
from foundrykit import AgentManager

manager = AgentManager()  # Uses get_foundry_client() internally
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `temporary_agent(**kwargs)` | Context manager: create → yield → auto-delete | Agent object |
| `run_agent(agent_id, thread_id)` | Synchronous run (blocks) | Run result |
| `run_agent_stream(agent_id, thread_id)` | Streaming run | Generator of `AgentStreamEvent` |

### Basic Usage
```python
with manager.temporary_agent(
    model="gpt-4.1-mini",
    name="my-agent",
    instructions="You are helpful.",
    toolset=registry.build_toolset(),
) as agent:
    # Agent exists only within this block — auto-deleted on exit
    thread = manager.client.agents_client.threads.create()
    manager.client.agents_client.messages.create(
        thread_id=thread.id, role="user", content="Hello"
    )
    result = manager.run_agent(agent.id, thread.id)
```

### Streaming Usage
```python
for event in manager.run_agent_stream(agent.id, thread.id):
    print(event.event_type, event.data)
```

### Extension — Custom event mapping:
```python
class MyAgentManager(AgentManager):
    def run_agent_stream(self, agent_id: str, thread_id: str):
        for event in super().run_agent_stream(agent_id, thread_id):
            # Map raw events to your domain events
            yield AgentStreamEvent(
                event_type=self._classify(event),
                data=event.data,
                metadata={"agent_id": agent_id},
            )
```

## ToolRegistry — Tool Registration + Tracing

```python
from foundrykit import ToolRegistry

registry = ToolRegistry()

@registry.register
def my_tool(query: str) -> str:
    """Clear docstring — the agent reads this to decide when to call."""
    return json.dumps({"result": "..."})

toolset = registry.build_toolset()  # → Azure SDK ToolSet
```

### How It Works
1. `@registry.register` wraps the function with an OpenTelemetry span (`tool.{name}`).
2. The wrapped function is stored in `registry._functions`.
3. `build_toolset()` converts all registered functions to `FunctionTool` + `ToolSet`.

### Rules
- Tool functions **must return `str`** (JSON-serialized).
- Tool functions **must accept simple types** (str, int, float, bool, list, dict).
- Tool **docstrings are required** — the agent uses them to decide when to call.
- Tool **names must match** the YAML spec `tools:` list exactly.

### Extension — Custom tracing:
```python
class TracedToolRegistry(ToolRegistry):
    def register(self, fn):
        wrapped = super().register(fn)
        # Add custom attributes to the span
        return wrapped
```

## Testing (with testkit fakes)

```python
from testkit import FakeFoundryClient, FakeAgentManager

# Test agent lifecycle without Azure credentials
manager = FakeAgentManager()
with manager.temporary_agent(name="test", model="gpt-4") as agent:
    assert agent.name == "test"
assert len(manager.created_agents) == 1
assert len(manager.deleted_agents) == 1

# Test with custom response
manager.set_run_response("custom answer")
result = manager.run_agent("agent-1", "thread-1")
assert result.content == "custom answer"
```

## File Map

| File | Contains |
|------|----------|
| `config.py` | `FoundrySettings` (Pydantic BaseSettings) |
| `client.py` | `FoundryClient`, `get_foundry_client()` |
| `agent.py` | `AgentManager`, `AgentStreamEvent` |
| `tools.py` | `ToolRegistry` |

## Checklist
- [ ] Using `get_foundry_client()` singleton (not direct `FoundryClient()`)
- [ ] `.env` has `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_CREDENTIAL_MODE`
- [ ] Tools return `str`, accept simple types, have docstrings
- [ ] Using `temporary_agent()` context manager for auto-cleanup
- [ ] Tests use `FakeFoundryClient` / `FakeAgentManager` from testkit
