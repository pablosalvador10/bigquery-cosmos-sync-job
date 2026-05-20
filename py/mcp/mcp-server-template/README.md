# MCP Server Template

Run locally:

```bash
cd py/mcp/mcp-server-template
uv pip install -e .
uv run uvicorn server:app --reload --port 8080
```

Add your own tool routing in `server.py` and organize implementations in `tools/`.
