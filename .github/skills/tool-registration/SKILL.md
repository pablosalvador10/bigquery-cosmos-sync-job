---
name: tool-registration
description: 'Registers a new agent tool via ToolRegistry with OpenTelemetry tracing. Use when creating a new tool function, adding a tool to an agent, or extending the tool surface.'
argument-hint: 'Describe the tool purpose (e.g., "search knowledge base by query")'
---

## Purpose
Step-by-step workflow for creating and registering a new agent tool in the template.

## When to Use
- Adding a new function the AI agent can call.
- Extending the tool surface for an existing agent.
- Wrapping an external API as an agent tool.

## Flow

1. **Write the tool function** in `py/apps/app-template/tools/`:
   - Create a new file or add to existing (e.g., `tools/my_tools.py`).
   - Function must accept simple types (str, int, float, bool, list, dict) — these map to agent tool parameters.
   - Function must return `str` (typically `json.dumps(result)`).
   - Add a clear docstring — the agent uses it to decide when to call the tool.
   - Example pattern from `tools/sample_tools.py`:
     ```python
     def summarize_text(text: str) -> str:
         """Summarize input text, returning JSON with summary and word count."""
         words = text.split()
         summary = " ".join(words[:min(len(words), 24)])
         return json.dumps({"summary": summary, "word_count": len(words)})
     ```

2. **Register with ToolRegistry**:
   - Import the registry instance (or create one).
   - Decorate with `@registry.register`:
     ```python
     from foundrykit import ToolRegistry
     registry = ToolRegistry()

     @registry.register
     def my_tool(query: str) -> str:
         ...
     ```
   - The decorator auto-wraps with OpenTelemetry tracing spans.

3. **Add to agent spec** (if using YAML-driven agents):
   - In the agent YAML spec, add the tool name to the `tools:` list.
   - The name must match the function name exactly.

4. **Build toolset for agent**:
   - Call `registry.build_toolset()` to get a `ToolSet` compatible with Azure Agents SDK.
   - Pass to `AgentManager.temporary_agent(tool_resources=...)`.

5. **Test the tool**:
   - Write a unit test calling the function directly.
   - Verify JSON output shape and edge cases.

## Decision Logic
- **Pure computation**: No decorator needed if tool is not exposed to agents — just a regular function.
- **Agent-callable**: Must be registered via `@registry.register` and return `str`.
- **External API call**: Use `httpx` with explicit timeout. Handle errors gracefully — return error JSON, don't raise.

## Checklist
- [ ] Function has clear docstring (agent reads this)
- [ ] Returns `str` (JSON-serialized)
- [ ] Registered with `@registry.register`
- [ ] Added to agent spec `tools:` list
- [ ] Unit test written
