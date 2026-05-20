# foundrykit

Reusable Azure AI Foundry helper library for agent lifecycle, credential management, tool registration, and OpenTelemetry tracing.

## Public API

```python
from foundrykit import (
    AgentManager,       # Agent lifecycle: create, run, stream, cleanup
    AgentStreamEvent,   # Streaming event container (event_type, data, metadata)
    FoundryClient,      # Azure connection wrapper (use via get_foundry_client)
    FoundrySettings,    # Pydantic settings for Foundry config
    ToolRegistry,       # Tool registration with auto OpenTelemetry tracing
    get_foundry_client, # Singleton factory — always use this
)
```

## Quick Start

### Register tools

```python
from foundrykit import ToolRegistry
import json

registry = ToolRegistry()

@registry.register
def search_faq(query: str) -> str:
    """Search the FAQ knowledge base."""
    return json.dumps({"answer": "Reset your password at /settings"})
```

### Create and run an agent

```python
from foundrykit import AgentManager

manager = AgentManager()

with manager.temporary_agent(
    model="gpt-4.1-mini",
    name="support-agent",
    instructions="You are a support assistant.",
    toolset=registry.build_toolset(),
) as agent:
    thread = manager.client.agents_client.threads.create()
    manager.client.agents_client.messages.create(
        thread_id=thread.id, role="user", content="How do I reset my password?"
    )
    result = manager.run_agent(agent.id, thread.id)
```

### Stream agent responses

```python
for event in manager.run_agent_stream(agent.id, thread.id):
    print(event.event_type, event.data)
```

## Classes

### `FoundrySettings`

Pydantic settings loaded from `.env`:

| Field | Default | Description |
|-------|---------|-------------|
| `foundry_project_endpoint` | `""` | Azure AI Foundry project URL |
| `foundry_model` | `"gpt-4.1-mini"` | Default model deployment name |
| `foundry_credential_mode` | `"dev"` | `"dev"` (DefaultAzureCredential) or `"managed_identity"` |
| `azure_client_id` | `None` | Client ID for managed identity mode |

### `FoundryClient`

Azure connection wrapper. **Always use `get_foundry_client()` instead of creating directly.**

- `agents_client` property: lazily-initialized `AgentsClient` from `azure-ai-agents` SDK.
- `_build_credential()`: returns `DefaultAzureCredential` (dev) or `ManagedIdentityCredential` (production).

### `AgentManager`

Agent lifecycle manager.

| Method | Purpose |
|--------|---------|
| `temporary_agent(**kwargs)` | Context manager — creates agent, yields it, auto-deletes on exit |
| `run_agent(agent_id, thread_id)` | Synchronous run — blocks until complete |
| `run_agent_stream(agent_id, thread_id)` | Generator — yields `AgentStreamEvent` objects |

### `ToolRegistry`

Tool registration with automatic OpenTelemetry tracing.

| Method | Purpose |
|--------|---------|
| `register(fn)` | Decorator — wraps function with `tool.{name}` OTel span |
| `build_toolset()` | Returns `ToolSet` compatible with Azure Agents SDK |

**Tool function rules:**
- Must return `str` (JSON-serialized).
- Must accept simple types (str, int, float, bool, list, dict).
- Must have a docstring (agent reads it to decide when to call).

## Configuration

Set these environment variables (or put them in `.env`):

```env
AZURE_FOUNDRY_PROJECT_ENDPOINT=https://your-foundry.services.ai.azure.com/api/projects/your-project
FOUNDRY_CREDENTIAL_MODE=dev          # "dev" for local, "managed_identity" for production
AZURE_CLIENT_ID=                     # Required only for managed_identity mode
```
