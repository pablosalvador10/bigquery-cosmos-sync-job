---
description: "Create a new AI agent with YAML spec, tools, system prompt, and endpoint wiring."
---

# New Agent

Help me create a new AI agent for this application.

## Steps

1. **Ask me** what the agent should do, what tools it needs, and its personality/tone.

2. **Create the YAML agent spec** in `py/apps/app-template/agents/`:
   - `name`, `model`, `instructions`, `tools` list.

3. **Write the system prompt** — either inline in YAML or as a separate `prompts/{name}.md` file if longer than 5 lines.

4. **Create tool functions** in `py/apps/app-template/tools/`:
   - Register each with `@registry.register` from foundrykit.
   - Each must return `str` (JSON) and have a docstring.

5. **Wire into an endpoint** — either modify the existing `/api/v1/chat` route to load the new spec, or create a new route.

6. **Test**:
   - Load test: verify YAML spec loads via `load_agent_spec()`.
   - Tool test: verify each tool returns valid JSON.
   - Endpoint test: verify SSE stream works end-to-end.
   ```bash
   cd py/apps/app-template && uv run python -m pytest tests/ -v
   ```

7. **Show me** the final agent spec, tools, prompt, and tests.
