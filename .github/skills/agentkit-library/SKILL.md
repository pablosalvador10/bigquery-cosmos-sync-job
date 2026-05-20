---
name: agentkit-library
description: 'Reference for using and extending agentkit — YAML-driven agent specification loading and validation. Use when defining agent specs, loading YAML configs, extending AgentSpec with custom fields, or managing multiple agent configurations.'
argument-hint: 'Describe what you need (e.g., "add temperature field to agent spec", "load spec with Jinja templating")'
---

## Purpose

Agentkit is the **configuration layer** for AI agents. It separates the "what" (name, model, prompt, tools) from the "how" (credentials, runtime). Agent specs are defined in YAML, loaded and validated via Pydantic.

## Public API Summary

| Export | Type | Purpose |
|--------|------|---------|
| `AgentSpec` | Pydantic `BaseModel` | Typed agent specification |
| `load_agent_spec(path)` | Function | Load + validate YAML → `AgentSpec` |

**Location:** `py/libs/agentkit/agentkit/`

## AgentSpec — Agent Configuration Model

```python
from agentkit import AgentSpec

class AgentSpec(BaseModel):
    name: str              # Unique agent identifier
    model: str             # Azure OpenAI deployment name
    instructions: str      # System prompt text
    tools: list[str] = []  # Function names matching @registry.register names
```

All fields are validated by Pydantic. Invalid YAML raises `ValidationError`.

## load_agent_spec — YAML Loader

```python
from agentkit import load_agent_spec

spec = load_agent_spec("agents/chat-agent.yaml")
print(spec.name)          # "chat-agent"
print(spec.model)         # "gpt-4.1-mini"
print(spec.instructions)  # "You are the template agent..."
print(spec.tools)         # ["summarize_text", "fetch_data_api"]
```

Accepts `str` or `Path`. Reads UTF-8, parses YAML, validates via Pydantic.

## YAML Spec Format

```yaml
# py/apps/app-template/agents/chat-agent.yaml
name: chat-agent
model: gpt-4.1-mini
instructions: |
  You are the template agent assistant.
  Provide clear, concise answers and prefer structured output.
  Use the summarize_text tool when processing long inputs.
tools:
  - summarize_text
  - fetch_data_api
```

### Conventions
- **One YAML file per agent** — stored in `agents/` directory.
- **`name`** must be unique across all agents in the app.
- **`model`** maps to an Azure OpenAI deployment name.
- **`instructions`** uses YAML `|` for multi-line strings.
- **`tools`** list must match registered function names exactly.
- **Long prompts** — for prompts > 20 lines, consider keeping them in `prompts/{name}.md` and loading separately.

## Extension Points

### Add custom fields to AgentSpec

Subclass `AgentSpec` and override `load_agent_spec`:

```python
from agentkit import AgentSpec
from pathlib import Path
import yaml

class ExtendedAgentSpec(AgentSpec):
    """Agent spec with additional domain-specific fields."""
    temperature: float = 0.7
    max_tokens: int = 4096
    tags: list[str] = []
    description: str = ""

def load_extended_spec(file_path: str | Path) -> ExtendedAgentSpec:
    path = Path(file_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ExtendedAgentSpec.model_validate(data)
```

Then in YAML:
```yaml
name: support-agent
model: gpt-4.1-mini
temperature: 0.3
max_tokens: 2048
tags: [support, customer-facing]
description: Handles customer support inquiries
instructions: |
  You are a customer support assistant...
tools:
  - search_faq
```

### Add Jinja templating to instructions

Agentkit depends on `jinja2` — use it for dynamic prompts:

```python
from jinja2 import Template
from agentkit import load_agent_spec

spec = load_agent_spec("agents/support-agent.yaml")
template = Template(spec.instructions)
rendered = template.render(
    company_name="Contoso",
    supported_languages=["English", "Spanish"],
)
# Pass `rendered` to AgentManager instead of spec.instructions
```

### Multiple agents with shared config

```python
from agentkit import load_agent_spec

AGENT_SPECS = {
    "chat": load_agent_spec("agents/chat-agent.yaml"),
    "support": load_agent_spec("agents/support-agent.yaml"),
    "research": load_agent_spec("agents/research-agent.yaml"),
}

def get_agent_spec(name: str) -> AgentSpec:
    return AGENT_SPECS[name]
```

## Integration with foundrykit

Agentkit provides the **spec**, foundrykit provides the **runtime**:

```python
from agentkit import load_agent_spec
from foundrykit import AgentManager, ToolRegistry

spec = load_agent_spec("agents/support-agent.yaml")
registry = ToolRegistry()
# ... register tools ...

manager = AgentManager()
with manager.temporary_agent(
    model=spec.model,
    name=spec.name,
    instructions=spec.instructions,
    toolset=registry.build_toolset(),
) as agent:
    # Use agent...
    pass
```

## Testing

```python
from pathlib import Path
from agentkit import load_agent_spec

def test_agent_spec(tmp_path: Path):
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text("""
name: test-agent
model: gpt-4.1-mini
instructions: Be helpful.
tools:
  - search
""".strip())

    spec = load_agent_spec(spec_file)
    assert spec.name == "test-agent"
    assert spec.model == "gpt-4.1-mini"
    assert "search" in spec.tools
```

## File Map

| File | Contains |
|------|----------|
| `loader.py` | `AgentSpec` model + `load_agent_spec()` function |
| `__init__.py` | Re-exports `AgentSpec`, `load_agent_spec` |

## Checklist
- [ ] YAML spec has `name`, `model`, `instructions`, `tools`
- [ ] Tool names in spec match `@registry.register` function names
- [ ] For custom fields, subclass `AgentSpec` instead of modifying agentkit
- [ ] Prompts > 20 lines stored in `prompts/` and loaded separately
- [ ] Tests validate spec loading from temp files
