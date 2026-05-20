# Library API Reference

## agentkit (`py/libs/agentkit`)

**Purpose**: Declarative agent configuration via YAML.

### Public API

| Export | Type | Purpose |
|--------|------|---------|
| `AgentSpec` | Pydantic `BaseModel` | Validated agent config (name, model, instructions, tools) |
| `load_agent_spec(path)` | Function | Reads YAML → returns `AgentSpec` |

### AgentSpec Fields

```python
class AgentSpec(BaseModel):
    name: str                           # Agent identifier (must be unique)
    model: str                          # Azure OpenAI deployment name
    instructions: str                   # System prompt text
    tools: list[str] = []               # Function names matching @registry.register
```

### YAML Format

```yaml
name: my-agent
model: gpt-4.1-mini
instructions: |
  You are a helpful assistant.
tools:
  - tool_function_name
```

### Dependencies
- `pyyaml` (YAML parsing)
- `jinja2` (template expansion, future use)
- `pydantic` (validation)

---

## foundrykit (`py/libs/foundrykit`)

**Purpose**: Azure AI Foundry runtime — credentials, agent lifecycle, tools, tracing.

### Public API

| Export | Type | Purpose |
|--------|------|---------|
| `FoundrySettings` | Pydantic `BaseSettings` | Env-based config (endpoint, model, credential mode) |
| `FoundryClient` | Class | Azure connection wrapper (credential handling, lazy AgentsClient) |
| `get_foundry_client()` | Function | Cached singleton factory — **always use this** |
| `AgentManager` | Class | Agent lifecycle (create, run, stream, cleanup) |
| `AgentStreamEvent` | Dataclass | Streaming event container (event_type, data, metadata) |
| `ToolRegistry` | Class | Tool registration with automatic OpenTelemetry tracing |

### FoundrySettings

```python
class FoundrySettings(BaseSettings):
    foundry_project_endpoint: str = ""       # Azure Foundry project URL
    foundry_model: str = "gpt-4.1-mini"      # Default model deployment
    foundry_credential_mode: "dev" | "managed_identity" = "dev"
    azure_client_id: str | None = None       # For managed identity mode
```

Loads from `.env` automatically. Extended by `AppSettings` in the app layer.

### FoundryClient

```python
client = get_foundry_client()          # Singleton — cached via @lru_cache
client.agents_client                   # → AgentsClient (lazy-initialized)
client._build_credential()             # → DefaultAzureCredential or ManagedIdentityCredential
```

**Credential modes**:
- `dev` → `DefaultAzureCredential` (uses `az login`, env vars, etc.)
- `managed_identity` → `ManagedIdentityCredential(client_id=azure_client_id)`

### AgentManager

```python
manager = AgentManager()               # Uses get_foundry_client() internally
manager = AgentManager(client=custom)  # Or inject a custom FoundryClient
```

| Method | Signature | Behavior |
|--------|-----------|----------|
| `temporary_agent(**kwargs)` | Context manager → yields Agent | Creates agent, yields, deletes on exit |
| `run_agent(agent_id, thread_id)` | → Run result | Synchronous: `runs.create_and_process()` |
| `run_agent_stream(agent_id, thread_id)` | → Generator[AgentStreamEvent] | Streaming: yields raw events |

**`temporary_agent` kwargs** (passed directly to `create_agent()`):
- `model` (str) — deployment name
- `name` (str) — agent display name
- `instructions` (str) — system prompt
- `toolset` (ToolSet) — from `registry.build_toolset()`
- Any other Azure SDK `create_agent()` parameter

### AgentStreamEvent

```python
@dataclass
class AgentStreamEvent:
    event_type: str                    # e.g., "raw"
    data: str = ""                     # Event payload
    metadata: dict[str, Any] = {}      # Additional context
```

### ToolRegistry

```python
registry = ToolRegistry()

@registry.register                     # Decorator — wraps with OTel span
def my_tool(arg: str) -> str:          # MUST return str (JSON)
    """Docstring — agent reads this.""" # MUST have docstring
    return json.dumps({...})

toolset = registry.build_toolset()     # → ToolSet with FunctionTool
```

**Tracing**: Every `@registry.register` call creates a span named `tool.{function_name}` with attribute `tool.name`.

**Constraints**:
- Function parameters: simple types only (str, int, float, bool, list, dict)
- Return type: `str` (JSON-serialized)
- Docstring: required — the agent uses it to decide when to invoke the tool

### Dependencies
- `azure-ai-agents` (Azure Agents SDK)
- `azure-identity` (credential providers)
- `pydantic-settings` (config)
- `structlog` (logging)
- `opentelemetry-api` (tracing)
