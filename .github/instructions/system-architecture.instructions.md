---
description: System architecture for the reusable Azure agentic app template. Read before making architectural or multi-file changes.
applyTo: '**'
---

# System Architecture

## Purpose
This repo is a reusable full-stack template for Azure-based agentic applications with real-time chat streaming.

## Top-Level Structure
- `py/`: Python workspace (`uv`) for backend apps and reusable libs.
- `ts/`: TypeScript workspace (`pnpm`) for frontend apps.
- `infra/`: Terraform + `azd` provisioning/deployment foundation.
- `docs/`: Architecture, setup, API, and troubleshooting docs.

## Runtime Components
- Backend app: `py/apps/app-template` (FastAPI).
- Reusable libs: `py/libs/foundrykit`, `py/libs/agentkit`.
- MCP template server: `py/mcp/mcp-server-template`.
- Frontend app: `ts/apps/ui-copilot-template` (React + Vite).

## Core Data Flow
1. Frontend sends message to `/api/v1/chat` or `/api/v1/chat/stream`.
2. Backend validates request and records user message via storage abstraction.
3. Backend generates assistant output (placeholder flow in template).
4. SSE stream emits `message_start`, `delta`, `tool_event`, `done`.
5. Frontend incrementally renders deltas and tool-state card.

## Storage Pattern
- Interface-first: `Storage` protocol in backend services.
- Backends:
  - `InMemoryStorage` for local/default flows.
  - `CosmosStorage` scaffold for cloud persistence.

## Infra Pattern
- Root `main.tf` composes individual modules from `infra/modules/`.
- Available modules: `log-analytics`, `application-insights`, `container-registry`, `container-apps-environment`, `container-app`, `cosmos-db`, `key-vault`.
- Feature flags (`enable_cosmos_db`, `enable_key_vault`) control optional resources.
- User-Assigned Managed Identity provides RBAC access to all Azure services.
- `azure.yaml` binds app services and infra for `azd` workflows.

## Change Impact Matrix
- Backend API contract change:
  - Must update frontend stream parser/types and API docs.
- SSE event schema change:
  - Must update backend emitter, frontend hook, and tests.
- Storage schema/partition key change:
  - Must update models, storage implementation, and infra docs.
- Infra resource naming/outputs change:
  - Must update `azure.yaml`, env examples, and deployment docs.

## Architecture Guardrails
- Keep reusable logic in `py/libs`, not app routes.
- Keep sample app domain-neutral and lightweight.
- Avoid introducing new orchestration layers unless required.
- Prefer explicit typed contracts across API boundaries.
