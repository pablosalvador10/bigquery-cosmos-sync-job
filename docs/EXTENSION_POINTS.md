# Extension Point Catalog

This document maps requirement categories to the exact template extension points, files, and patterns. Use this when planning implementation tasks — every task should reference a specific extension point.

## Template Layers

| Layer | Path | Purpose |
|-------|------|---------|
| **foundrykit** | `py/libs/foundrykit` | Azure AI Foundry client, AgentManager, ToolRegistry |
| **agentkit** | `py/libs/agentkit` | YAML-driven agent spec loader |
| **evalkit** | `py/libs/evalkit` | Domain-agnostic evaluation framework |
| **synthetickit** | `py/libs/synthetickit` | Synthetic data generation pipeline |
| **testkit** | `py/libs/testkit` | Shared test utilities and fakes |
| **backend** | `py/apps/app-template` | FastAPI backend (chat, SSE streaming, storage) |
| **mcp** | `py/mcp/mcp-server-template` | MCP HTTP server skeleton |
| **frontend** | `ts/apps/ui-copilot-template` | React chat UI with SSE parsing |
| **infra** | `infra/` | Terraform modules + azd deployment |

## Extension Point Reference

### AI Agent

| Aspect | Details |
|--------|---------|
| **Layer** | agentkit + foundrykit |
| **What to do** | Create YAML agent spec, load via `load_agent_spec()`, run via `AgentManager` |
| **Key files** | `py/apps/app-template/agents/*.yaml` |
| **Libraries** | `agentkit.load_agent_spec()`, `foundrykit.AgentManager` |
| **Pattern** | Define in YAML (name, model, instructions, tools), load at startup, use `temporary_agent()` context manager |

### Agent Tool

| Aspect | Details |
|--------|---------|
| **Layer** | foundrykit |
| **What to do** | Create tool function, register with `@registry.register`, add to agent YAML |
| **Key files** | `py/apps/app-template/tools/*.py` |
| **Libraries** | `foundrykit.ToolRegistry` |
| **Pattern** | Function returns `str` (JSON), has a docstring the agent reads, auto-traced via OpenTelemetry |

### API Endpoint

| Aspect | Details |
|--------|---------|
| **Layer** | backend |
| **What to do** | Create route file, define Pydantic models, wire router in `main.py` |
| **Key files** | `py/apps/app-template/api/v1/*.py`, `models/*.py`, `main.py` |
| **Pattern** | `APIRouter(prefix="/api/v1")`, async handlers, Pydantic request/response models |

### SSE Streaming

| Aspect | Details |
|--------|---------|
| **Layer** | backend + frontend |
| **What to do** | Use `_sse()` helper for backend, `streamChat()` + `useStreamingChat` for frontend |
| **Key files** | `api/v1/chat.py`, `ts/apps/ui-copilot-template/src/lib/api.ts`, `hooks/useStreamingChat.ts` |
| **Contract** | Events: `message_start` → `delta` (repeated) → `tool_event` (optional) → `done` |

### Data Persistence

| Aspect | Details |
|--------|---------|
| **Layer** | backend + infra |
| **What to do** | Implement `Storage` protocol, add Cosmos implementation, update `get_storage()` factory |
| **Key files** | `services/storage.py`, `infra/modules/cosmos-db/main.tf` |
| **Pattern** | Protocol with `add_message()` / `list_messages()`, factory selects InMemory vs Cosmos via env var |

### Domain Models

| Aspect | Details |
|--------|---------|
| **Layer** | backend |
| **What to do** | Define Pydantic models with `Field()`, UUIDs, timestamps |
| **Key files** | `py/apps/app-template/models/*.py` |
| **Pattern** | `BaseModel` subclasses, `Field(default_factory=...)` for auto-generated values |

### UI Component

| Aspect | Details |
|--------|---------|
| **Layer** | frontend |
| **What to do** | Create functional React component with TailwindCSS |
| **Key files** | `ts/apps/ui-copilot-template/src/components/*.tsx` |
| **Pattern** | Functional component, props interface, import in `App.tsx` |

### UI State / Hook

| Aspect | Details |
|--------|---------|
| **Layer** | frontend |
| **What to do** | Create custom React hook with `useCallback`/`useMemo` |
| **Key files** | `ts/apps/ui-copilot-template/src/hooks/*.ts` |
| **Pattern** | Return memoized state and actions from hook |

### UI API Integration

| Aspect | Details |
|--------|---------|
| **Layer** | frontend |
| **What to do** | Add fetch calls with SSE parsing for streaming endpoints |
| **Key files** | `ts/apps/ui-copilot-template/src/lib/api.ts` |
| **Pattern** | `fetch()` with `ReadableStream` reader for SSE |

### Azure Resource

| Aspect | Details |
|--------|---------|
| **Layer** | infra |
| **What to do** | Create Terraform module with variables/outputs, wire in `main.tf` |
| **Key files** | `infra/modules/*/main.tf`, `infra/main.tf`, `infra/variables.tf`, `infra/outputs.tf` |
| **Pattern** | Module with variables → resources → outputs, RBAC via managed identity |

### Auth / Identity

| Aspect | Details |
|--------|---------|
| **Layer** | infra + backend |
| **What to do** | Configure managed identity, wire credential mode in settings |
| **Key files** | `foundrykit.FoundrySettings`, `infra/main.tf` (identity block) |
| **Pattern** | `DefaultAzureCredential` (dev), `ManagedIdentityCredential` (prod) |

### Telemetry / Observability

| Aspect | Details |
|--------|---------|
| **Layer** | backend |
| **What to do** | Use existing telemetry layer, configure exporters via env vars |
| **Key files** | `core/telemetry.py`, `core/logging.py`, `.env` |
| **Pattern** | structlog for structured logging, OpenTelemetry for tracing, configurable exporter (console / OTLP / Azure Monitor) |

### MCP Tool

| Aspect | Details |
|--------|---------|
| **Layer** | mcp |
| **What to do** | Create tool module, register in dispatch router |
| **Key files** | `py/mcp/mcp-server-template/tools/*.py`, `server.py` |
| **Pattern** | Add tool handler function, register in `mcp_dispatch()` |

### Evaluation Pipeline

| Aspect | Details |
|--------|---------|
| **Layer** | evalkit |
| **What to do** | Define domain `EvalContext`, create evaluators, configure rubric |
| **Key files** | `py/libs/evalkit/evalkit/` |
| **Libraries** | `evalkit.Evaluator` protocol, `evalkit.EvalRubric`, `evalkit.EvalContext` |
| **Pattern** | Create evaluator implementing `dimension` + `evaluate()`, register in rubric with weights |

### Synthetic Data Generation

| Aspect | Details |
|--------|---------|
| **Layer** | synthetickit |
| **What to do** | Define scenarios, configure pipeline, implement generate/classify functions |
| **Key files** | `py/libs/synthetickit/synthetickit/` |
| **Libraries** | `synthetickit.PipelineConfig`, `synthetickit.run_pipeline`, `synthetickit.Scenario` |
| **Pattern** | YAML scenarios, 3-stage pipeline (prepare → synthesize → annotate), quality gates |

### Test Infrastructure

| Aspect | Details |
|--------|---------|
| **Layer** | testkit |
| **What to do** | Import fakes from testkit, seed in conftest fixtures |
| **Key files** | `py/libs/testkit/testkit/` |
| **Libraries** | `testkit.FakeCosmosContainer`, `testkit.FakeLLMClient`, `testkit.FakeStorage`, `testkit.FakeFoundryClient` |
| **Pattern** | Create fixtures using fakes, seed test data, use assertion helpers |

### App Configuration

| Aspect | Details |
|--------|---------|
| **Layer** | backend |
| **What to do** | Extend `AppSettings(FoundrySettings)` with new fields |
| **Key files** | `core/config.py`, `.env`, `.env.example` |
| **Pattern** | `pydantic-settings` with env var loading, `.env` for local dev |

### Docker / Local Dev

| Aspect | Details |
|--------|---------|
| **Layer** | docker |
| **What to do** | Update Dockerfile and docker-compose.yml |
| **Key files** | `py/apps/app-template/Dockerfile`, `docker-compose.yml` |
| **Pattern** | Multi-service compose with health checks |

### CI Pipeline

| Aspect | Details |
|--------|---------|
| **Layer** | github |
| **What to do** | Update workflow to include new libs in test matrix |
| **Key files** | `.github/workflows/ci.yml` |
| **Pattern** | Python lint (ruff) + test (pytest) + TS lint + typecheck + test + build |

## Template-Aware Task Categories

When planning tasks, use these categories instead of generic roles:

| Category | Maps To |
|----------|---------|
| `infra-foundation` | Infrastructure layer |
| `evalkit-core` | evalkit library |
| `synthetickit-core` | synthetickit library |
| `domain-design` | Backend models |
| `agent-config` | agentkit YAML specs |
| `tool-registration` | foundrykit ToolRegistry |
| `backend-routes` | Backend API endpoints |
| `backend-models` | Backend Pydantic models |
| `backend-orchestration` | Backend services |
| `storage-cosmos` | Storage + Cosmos integration |
| `frontend-components` | React components |
| `frontend-hooks` | React hooks |
| `frontend-api-integration` | Frontend API layer |
| `observability` | Telemetry + logging |
| `integration-validation` | Integration tests |
| `load-testing` | Performance tests |
| `smoke-testing` | Deployment checks |
| `release-readiness` | Release checklist |
