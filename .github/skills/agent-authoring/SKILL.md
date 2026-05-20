---
name: agent-authoring
description: 'Creates a new AI agent using YAML specs, foundrykit AgentManager, and ToolRegistry. Use when building a new agent, defining agent behavior, writing agent specs, or configuring agent tools and prompts. Covers which library to use for each concern: agentkit for spec/config, foundrykit for runtime/credentials/tools.'
argument-hint: 'Describe the agent purpose (e.g., "customer support agent with FAQ lookup")'
---

## Purpose
Step-by-step workflow for creating a new Azure AI Foundry agent. Explains **which library handles what** so you pick the right abstraction for each decision.

## When to Use
- Building a new AI agent from scratch.
- Deciding whether to use `agentkit` (config), `foundrykit` (runtime), or both.
- Wiring tools, credentials, and streaming into an agent.

## Library Decision Map

Two libraries, two concerns. Never mix them:

| Concern | Library | Key Class | Location |
|---------|---------|-----------|----------|
| **What** the agent is (name, model, prompt, tool list) | `agentkit` | `AgentSpec`, `load_agent_spec()` | `py/libs/agentkit/` |
| **How** the agent runs (credentials, API calls, streaming, tracing) | `foundrykit` | `FoundryClient`, `AgentManager`, `ToolRegistry` | `py/libs/foundrykit/` |

### `agentkit` — Agent Configuration (the "what")

**`AgentSpec`** (Pydantic model):
```python
class AgentSpec(BaseModel):
    name: str           # Unique agent identifier
    model: str          # Azure OpenAI deployment name (e.g., "gpt-4.1-mini")
    instructions: str   # System prompt text
    tools: list[str]    # Function names that match @registry.register names
```

**`load_agent_spec(path)`**: Reads a YAML file → returns validated `AgentSpec`.
```python
from agentkit import load_agent_spec
spec = load_agent_spec("agents/my-agent.yaml")
# spec.name, spec.model, spec.instructions, spec.tools are all typed
```

**When to use agentkit**:
- Defining agent behavior declaratively (YAML).
- Managing multiple agent configs (one YAML per agent).
- Keeping prompts and tool lists version-controlled and reviewable.

**When NOT to use agentkit**:
- If agent config is fully dynamic (decided at runtime) — construct `create_agent()` kwargs directly.

### `foundrykit` — Agent Runtime (the "how")

Four classes, each with a specific job:

**1. `FoundrySettings`** (Pydantic settings — environment config):
```python
class FoundrySettings(BaseSettings):
    foundry_project_endpoint: str   # Azure AI Foundry project URL
    foundry_model: str              # Default model (gpt-4.1-mini)
    foundry_credential_mode: "dev" | "managed_identity"
    azure_client_id: str | None     # For managed identity
```
- Loads from `.env` automatically. Never hardcode these.
- `AppSettings` in the app layer extends this — add app-specific config there, not here.

**2. `FoundryClient`** (Azure connection — singleton):
```python
from foundrykit import get_foundry_client
client = get_foundry_client()  # Cached singleton — NEVER create FoundryClient() directly
client.agents_client            # Lazy-init AgentsClient from Azure SDK
```
- `dev` mode → `DefaultAzureCredential` (uses `az login`).
- `managed_identity` mode → `ManagedIdentityCredential` (production Container Apps).
- The `agents_client` property gives you the raw Azure `AgentsClient` for low-level operations.

**3. `AgentManager`** (agent lifecycle — create, run, stream):
```python
from foundrykit import AgentManager
manager = AgentManager()  # Uses get_foundry_client() internally
```

Three methods:

| Method | Purpose | Returns |
|--------|---------|---------|
| `temporary_agent(**kwargs)` | Context manager: creates agent → yields it → auto-deletes on exit | Agent object |
| `run_agent(agent_id, thread_id)` | Synchronous run — blocks until agent completes | Run result |
| `run_agent_stream(agent_id, thread_id)` | Streaming run — yields `AgentStreamEvent` objects | Generator of events |

**4. `ToolRegistry`** (tool registration + tracing):
```python
from foundrykit import ToolRegistry
registry = ToolRegistry()

@registry.register
def my_tool(query: str) -> str:
    """Docstring the agent reads to decide when to call this."""
    return json.dumps({"result": "..."})

toolset = registry.build_toolset()  # → ToolSet for Azure SDK
```
- `@registry.register` wraps every call with an OpenTelemetry span (`tool.{name}`).
- `build_toolset()` converts registered functions to `FunctionTool` + `ToolSet`.
- Tool functions MUST return `str` (JSON) and accept simple types.

## Flow

### Step 1: Define the agent spec (agentkit)
Create `py/apps/app-template/agents/{name}.yaml`:
```yaml
name: support-agent
model: gpt-4.1-mini
instructions: |
  You are a customer support assistant. Use the search_faq tool
  to find answers. Be concise and cite sources.
tools:
  - search_faq
  - create_ticket
```

For long prompts, create `prompts/{name}.md` and load separately:
```python
spec = load_agent_spec("agents/support-agent.yaml")
prompt = Path("prompts/support-agent.md").read_text()
# Override: spec.instructions is from YAML, but you can pass prompt directly to create_agent
```

### Step 2: Register tools (foundrykit ToolRegistry)
```python
# py/apps/app-template/tools/support_tools.py
import json
from foundrykit import ToolRegistry

registry = ToolRegistry()

@registry.register
def search_faq(query: str) -> str:
    """Search the FAQ knowledge base for answers matching the query."""
    # ... implementation ...
    return json.dumps({"answer": "...", "source": "..."})

@registry.register
def create_ticket(subject: str, description: str) -> str:
    """Create a support ticket for issues that need human follow-up."""
    # ... implementation ...
    return json.dumps({"ticket_id": "T-1234", "status": "created"})
```

### Step 3: Create and run the agent (foundrykit AgentManager)
```python
from agentkit import load_agent_spec
from foundrykit import AgentManager
from tools.support_tools import registry

spec = load_agent_spec("agents/support-agent.yaml")
manager = AgentManager()

# Ephemeral agent — auto-deleted when context exits
with manager.temporary_agent(
    model=spec.model,
    name=spec.name,
    instructions=spec.instructions,
    toolset=registry.build_toolset(),
) as agent:
    # Create conversation thread
    thread = manager.client.agents_client.threads.create()
    manager.client.agents_client.messages.create(
        thread_id=thread.id, role="user", content="How do I reset my password?"
    )

    # Option A: Synchronous (blocks until done)
    result = manager.run_agent(agent.id, thread.id)

    # Option B: Streaming (yields events)
    for event in manager.run_agent_stream(agent.id, thread.id):
        print(event.event_type, event.data)
```

### Step 4: Wire into a streaming SSE endpoint
Map `AgentStreamEvent` to the SSE contract:
```python
async def _agent_stream(body: ChatRequest) -> AsyncGenerator[str, None]:
    spec = load_agent_spec("agents/support-agent.yaml")
    manager = AgentManager()

    with manager.temporary_agent(
        model=spec.model, name=spec.name,
        instructions=spec.instructions, toolset=registry.build_toolset(),
    ) as agent:
        thread = manager.client.agents_client.threads.create()
        manager.client.agents_client.messages.create(
            thread_id=thread.id, role="user", content=body.message
        )
        yield _sse("message_start", {"session_id": body.session_id, "message_id": body.message_id})

        for event in manager.run_agent_stream(agent.id, thread.id):
            yield _sse("delta", {"token": event.data})

        yield _sse("done", {"ok": True})
```

### Step 5: Test
```python
# Unit test: spec loading
def test_agent_spec():
    spec = load_agent_spec("agents/support-agent.yaml")
    assert spec.name == "support-agent"
    assert "search_faq" in spec.tools

# Unit test: tool output
def test_search_faq():
    result = json.loads(search_faq("password reset"))
    assert "answer" in result
```

## Decision Logic

| Scenario | agentkit | foundrykit | Approach |
|----------|----------|------------|----------|
| **Standard agent** (fixed config) | `load_agent_spec()` | `AgentManager` + `ToolRegistry` | YAML spec → load → run |
| **Dynamic agent** (runtime config) | Skip | `AgentManager` + `ToolRegistry` | Build kwargs in code → `temporary_agent()` |
| **Agent without tools** | `load_agent_spec()` | `AgentManager` only | YAML spec with empty tools list |
| **Multiple agents** | One YAML per agent | Shared `FoundryClient` singleton | Load different specs, same manager |
| **Custom credentials** | N/A | `FoundrySettings` | Set `FOUNDRY_CREDENTIAL_MODE` + `AZURE_CLIENT_ID` |

## Anti-Patterns
- **Creating `FoundryClient()` directly** — use `get_foundry_client()` singleton.
- **Hardcoding model names** — put in YAML spec or `FoundrySettings`.
- **Mixing config and runtime in one place** — agentkit defines the "what", foundrykit handles the "how".
- **Not cleaning up agents** — always use `temporary_agent()` context manager to auto-delete.
- **Registering tools without docstrings** — the agent reads the docstring to decide when to call tools.

## Checklist
- [ ] YAML spec created with `name`, `model`, `instructions`, `tools`
- [ ] System prompt is clear and scoped
- [ ] All tools registered with `@registry.register` + docstrings
- [ ] Tool names in YAML match registered function names exactly
- [ ] Using `get_foundry_client()` singleton (not direct `FoundryClient()`)
- [ ] Using `temporary_agent()` context manager (auto-cleanup)
- [ ] `.env` has `AZURE_FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_CREDENTIAL_MODE`
- [ ] Streaming endpoint maps events to SSE contract (if API-facing)
- [ ] Tests cover spec loading, tool output, and agent wiring
