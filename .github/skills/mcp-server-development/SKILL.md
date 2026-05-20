---
name: mcp-server-development
description: 'Builds or extends an MCP (Model Context Protocol) server with new tools. Use when creating MCP tools, adding MCP endpoints, building an MCP server, or extending mcp-server-template.'
argument-hint: 'Describe the MCP tool (e.g., "knowledge base search tool", "database query tool")'
---

## Purpose
Step-by-step workflow for building or extending the MCP HTTP server at `py/mcp/mcp-server-template`.

## When to Use
- Adding a new tool to the MCP server.
- Building a domain-specific MCP server from the template.
- Connecting an MCP server to the main application.

## Flow

1. **Understand the MCP server structure**:
   - `server.py`: FastAPI app with `/healthz` and `/mcp` endpoints.
   - `tools/`: Directory for tool implementations.
   - Request format: `{"tool": "tool_name", "arguments": {...}}`.
   - Response format: `{"tool": "...", "result": "...", "arguments": {...}}`.

2. **Add a tool function** in `py/mcp/mcp-server-template/tools/`:
   - Create `{domain}.py` with the tool logic:
     ```python
     def search_knowledge(query: str, top_k: int = 5) -> dict:
         """Search the knowledge base and return relevant results."""
         # Implementation here
         return {"results": [...], "query": query, "count": len(results)}
     ```

3. **Register in the dispatcher** — update `server.py`:
   ```python
   from tools.knowledge import search_knowledge

   @app.post("/mcp")
   async def mcp_dispatch(request: MCPRequest) -> dict:
       if request.tool == "search_knowledge":
           result = search_knowledge(**request.arguments)
           return {"tool": request.tool, "result": result, "arguments": request.arguments}
       # ... existing tools ...
   ```

4. **Add dependencies** (if needed):
   - Update `py/mcp/mcp-server-template/pyproject.toml` with new packages.
   - Keep dependencies minimal — only what the tool needs.

5. **Configure connection** in the main app:
   - Set `MCP_SERVER_URL` in `.env` (default: `http://localhost:8080/mcp`).
   - Call MCP tools via `httpx` from the backend app.

6. **Containerize** — `Dockerfile` already exists:
   - Builds the server as a standalone container.
   - Add to `docker-compose.yml` for local dev if running alongside the main app.

7. **Test**:
   ```bash
   cd py/mcp/mcp-server-template
   uv run uvicorn server:app --port 8080
   curl -X POST http://localhost:8080/mcp \
     -H "Content-Type: application/json" \
     -d '{"tool": "search_knowledge", "arguments": {"query": "test"}}'
   ```

## Decision Logic
- **Simple tool** (no external deps): Add directly in `tools/` + register in dispatcher.
- **Complex tool** (external API/DB): Add dependencies to `pyproject.toml`, handle errors gracefully.
- **Separate MCP server**: Clone `mcp-server-template/` to a new directory, customize independently.

## Checklist
- [ ] Tool function has clear docstring
- [ ] Registered in `mcp_dispatch()` switch
- [ ] Dependencies added to `pyproject.toml` (if any)
- [ ] Returns structured dict result
- [ ] Error handling for external calls
- [ ] Tested via curl or httpx
