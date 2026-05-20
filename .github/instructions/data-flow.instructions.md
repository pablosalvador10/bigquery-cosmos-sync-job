---
description: "End-to-end data flow from user message to rendered response. Read when tracing request lifecycle, debugging cross-layer issues, or understanding how components connect."
---

# Data Flow

## Request Lifecycle

A user message flows through these stages:

### 1. Frontend → Backend
- User types in chat UI (`App.tsx`)
- `useStreamingChat` hook calls `streamChat()` in `lib/api.ts`
- POST to `/api/v1/chat/stream` with `{ session_id, message_id, message, history }`

### 2. Backend: Route → Storage → Agent
- `chat.py` → `chat_stream()` handler receives `ChatRequest` (Pydantic validated)
- User message stored via `Storage.add_message()` (InMemory or Cosmos DB)
- `_foundry_available()` checks if `AZURE_FOUNDRY_PROJECT_ENDPOINT` is set

### 3a. Agent Mode (credentials configured)
- `load_agent_spec("agents/chat-agent.yaml")` → `AgentSpec` (agentkit)
- `AgentManager().temporary_agent()` → creates ephemeral agent (foundrykit)
- Tools from `ToolRegistry` (`@registry.register` in `tools/sample_tools.py`) → `build_toolset()`
- `run_agent_stream()` → yields `AgentStreamEvent` objects
- Events mapped to SSE format

### 3b. Simulation Mode (no credentials)
- `_load_system_prompt()` reads `prompts/system.md`
- `summarize_text()` called directly (bypasses agent)
- Reply split into tokens for SSE streaming

### 4. SSE Stream
Events emitted in order:
1. `message_start` → `{ session_id, message_id }`
2. `delta` (repeated) → `{ token }` per streamed token
3. `tool_event` → `{ tool, status }` (tool execution updates)
4. `done` → `{ ok: true }`

### 5. Frontend: Parse → Render
- `streamChat()` reads SSE stream, splits on `\n\n` boundaries
- `delta` events → tokens appended to assistant message via `setMessages()`
- `tool_event` → `ToolEvent` state → `ToolCard` component renders
- `done` → `setLoading(false)`

### 6. Storage
- Assistant response stored via `Storage.add_message()` after streaming completes
- Partition key `/session_id` ensures session isolation in Cosmos DB

## Component Wiring

```
agents/chat-agent.yaml  ←──  agentkit loads spec
        │
        ▼
tools/sample_tools.py   ←──  @registry.register decorates tools
        │
        ▼
api/v1/chat.py          ←──  foundrykit AgentManager runs agent
        │
        ▼
services/storage.py     ←──  Storage protocol persists messages
        │
        ▼
core/config.py          ←──  AppSettings (extends FoundrySettings) loads .env
```

## Cross-Layer Impact Rules
- **Change SSE event schema** → update backend emitter (`chat.py`) + frontend parser (`api.ts`) + types (`types.ts`) + tests
- **Change storage schema** → update `StoredMessage` model + storage implementations + Cosmos container config
- **Change agent spec** → update YAML file + ensure tool names match registered functions
- **Change infra outputs** → update `azure.yaml` bindings + `.env.azure.example`
