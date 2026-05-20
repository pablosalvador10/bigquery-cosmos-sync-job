# Architecture

## Overview

This template is a full-stack monorepo for Azure-first agentic applications with real-time chat streaming.

## Components

| Component | Location | Technology |
|-----------|----------|------------|
| Backend API | `py/apps/app-template` | FastAPI, Python 3.11+ |
| Foundry helpers | `py/libs/foundrykit` | Azure AI Agents SDK, OpenTelemetry |
| Agent config | `py/libs/agentkit` | YAML, Pydantic |
| MCP server | `py/mcp/mcp-server-template` | FastAPI |
| Frontend UI | `ts/apps/ui-copilot-template` | React 19, Vite, TypeScript |
| Infrastructure | `infra/` | Terraform, azd |

## End-to-End Data Flow

```
User types message in chat UI
  │
  ▼
Frontend: POST /api/v1/chat/stream
  │  Body: { session_id, message_id, message, history }
  │
  ▼
Backend: chat.py → _stream_reply()
  │
  ├─ 1. Store user message via Storage protocol (InMemory or Cosmos DB)
  │
  ├─ 2. Check _foundry_available()
  │     │
  │     ├─ YES (credentials configured):
  │     │   ├─ Load agent spec from agents/chat-agent.yaml (agentkit)
  │     │   ├─ Create ToolRegistry + register tools (@registry.register)
  │     │   ├─ AgentManager.temporary_agent() → create ephemeral agent
  │     │   ├─ Create thread + add user message via agents_client
  │     │   ├─ run_agent_stream() → yield AgentStreamEvent objects
  │     │   └─ Map events to SSE: delta tokens
  │     │
  │     └─ NO (local/simulation mode):
  │         ├─ Load system prompt from prompts/system.md
  │         ├─ Call summarize_text tool directly
  │         └─ Split reply into tokens for SSE streaming
  │
  ├─ 3. Emit SSE events:
  │     ├─ event: message_start  →  { session_id, message_id }
  │     ├─ event: delta          →  { token }  (repeated per token)
  │     ├─ event: tool_event     →  { tool, status }
  │     └─ event: done           →  { ok: true }
  │
  ├─ 4. Store assistant message via Storage protocol
  │
  └─ 5. Log completion via structlog
  │
  ▼
Frontend: streamChat() in lib/api.ts
  │
  ├─ Parse SSE stream (split on \n\n boundaries)
  ├─ delta events → append tokens to assistant message (useStreamingChat hook)
  ├─ tool_event → update ToolEvent state → render ToolCard component
  └─ done → mark loading complete
```

## Library Architecture

```
┌─────────────────────────────┐
│  py/apps/app-template       │  ← Domain logic, routes, tools
│  ├── api/v1/chat.py         │
│  ├── tools/sample_tools.py  │
│  ├── agents/chat-agent.yaml │
│  └── services/storage.py    │
└────────┬────────────────────┘
         │ imports
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│agentkit│ │foundrykit│  ← Reusable libraries
│       │ │         │
│AgentSp│ │Foundry  │
│ec     │ │Client   │
│       │ │Agent    │
│load_  │ │Manager  │
│agent_ │ │Tool     │
│spec() │ │Registry │
└───────┘ └─────────┘
```

**Separation of concerns:**
- `agentkit` defines **what** an agent is (YAML spec → `AgentSpec`).
- `foundrykit` handles **how** it runs (credentials, SDK calls, tracing).
- `app-template` is the **domain layer** (routes, tools, storage, prompts).

## Storage Architecture

```
Storage Protocol (typing.Protocol)
  ├── add_message(StoredMessage) → StoredMessage
  └── list_messages(session_id) → list[StoredMessage]

Implementations:
  ├── InMemoryStorage      ← Local dev (default)
  └── CosmosStorage        ← Production (STORAGE_MODE=cosmos)

Factory: get_storage() selects implementation via STORAGE_MODE env var
Partition key: /session_id (Cosmos DB)
```

## Infrastructure Architecture

```
Azure Resource Group
  ├── Container App Environment
  │   ├── Backend Container App (FastAPI)
  │   └── Frontend Container App (React/nginx)
  ├── Cosmos DB Account (Session consistency)
  │   └── SQL Database
  │       ├── messages container (partition: /session_id)
  │       └── sessions container (partition: /session_id)
  ├── Log Analytics Workspace
  └── Application Insights
```

Deployed via `azd provision` (Terraform) + `azd deploy` (container builds).
