---
description: "Create a new agent tool with registration, OpenTelemetry tracing, testing, and wiring to the agent spec."
---

# New Agent Tool

Help me create a new agent tool end-to-end.

## Steps

1. **Ask me** what the tool should do (input, output, external services).

2. **Create the tool function** in `py/apps/app-template/tools/`:
   - Accepts simple types, returns JSON string.
   - Clear docstring (the agent reads this to decide when to call).
   - Handle errors gracefully — return error JSON, don't raise.

3. **Register** with `@registry.register` from `foundrykit.ToolRegistry`.

4. **Add to agent YAML spec** (tools list).

5. **Write a unit test** calling the function directly with sample input.

6. **Run tests** to verify:
   ```bash
   cd py/apps/app-template && uv run pytest tests/ -v
   ```

7. **Show me** the final tool function, test, and updated agent spec.
