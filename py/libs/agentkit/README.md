# agentkit

YAML-driven agent configuration loader. Defines **what** an agent is (name, model, prompt, tools) while `foundrykit` handles **how** it runs.

## Public API

```python
from agentkit import AgentSpec, load_agent_spec
```

## Quick Start

### Define an agent spec

Create a YAML file (e.g., `agents/chat-agent.yaml`):

```yaml
name: chat-agent
model: gpt-4.1-mini
instructions: |
  You are a helpful assistant.
  Use the summarize_text tool for long inputs.
tools:
  - summarize_text
  - fetch_data_api
```

### Load and use the spec

```python
from agentkit import load_agent_spec
from foundrykit import AgentManager, ToolRegistry

spec = load_agent_spec("agents/chat-agent.yaml")

# spec.name          → "chat-agent"
# spec.model         → "gpt-4.1-mini"
# spec.instructions  → "You are a helpful assistant..."
# spec.tools         → ["summarize_text", "fetch_data_api"]

manager = AgentManager()
with manager.temporary_agent(
    model=spec.model,
    name=spec.name,
    instructions=spec.instructions,
    toolset=registry.build_toolset(),
) as agent:
    ...
```

## AgentSpec Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique agent identifier |
| `model` | `str` | Yes | Azure OpenAI deployment name |
| `instructions` | `str` | Yes | System prompt text |
| `tools` | `list[str]` | No | Function names matching `@registry.register` names |

## When to Use

- **Use agentkit** when agent config is static/declarative — one YAML per agent, version-controlled.
- **Skip agentkit** when agent config is fully dynamic (built at runtime from user input or DB).

## Dependencies

- `pyyaml` — YAML parsing
- `pydantic` — validation
- `jinja2` — template expansion (future use)
