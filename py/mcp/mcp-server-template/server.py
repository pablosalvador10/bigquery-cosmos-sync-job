from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-server-template", version="0.1.0")


class MCPRequest(BaseModel):
    tool: str
    arguments: dict


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mcp")
async def mcp_dispatch(request: MCPRequest) -> dict:
    if request.tool == "ping":
        return {"tool": "ping", "result": "pong", "arguments": request.arguments}

    return {
        "tool": request.tool,
        "result": "not_implemented",
        "arguments": request.arguments,
        "message": "Add your domain tools under py/mcp/mcp-server-template/tools/",
    }
