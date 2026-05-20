# Template Agentic AI Apps on Azure

Reusable full-stack foundation for building autonomous agent applications with:

- Python backend (`FastAPI`) with sync and SSE chat endpoints
- Reusable internal libs (`foundrykit`, `agentkit`)
- React chat UI template with streaming rendering
- MCP server skeleton for tool microservices
- Terraform + `azd` deployment baseline

## Monorepo Layout

- `py/apps/app-template`: Backend sample app (domain-neutral)
- `py/apps/sample-eval-e2e`: End-to-end sample (synthetickit + evalkit)
- `py/libs/foundrykit`: Foundry client/agent/tool abstractions
- `py/libs/agentkit`: YAML-driven agent spec loader
- `py/libs/evalkit`: Domain-agnostic evaluation framework
- `py/libs/synthetickit`: Synthetic data generation pipeline
- `py/libs/testkit`: Shared test fakes and utilities
- `py/mcp/mcp-server-template`: Generic MCP server starter
- `ts/apps/ui-copilot-template`: Streaming chat frontend template
- `infra/`: Terraform modules and environment scaffold
- `docs/`: Architecture, setup, API, troubleshooting

## Quick Start

### 1. Backend

```bash
cd py
uv sync --all-packages
uv run uvicorn --app-dir apps/app-template main:app --reload --port 8001
```

### 2. Frontend

```bash
cd ts
pnpm install
pnpm --filter ui-copilot-template dev
```

### 3. Run Tests

```bash
cd py && uv run pytest libs/ apps/ -v
```

### 4. Local End-to-End (Docker)

```bash
cp .env.example .env
docker compose up --build
```

## Streaming Contract

Backend SSE endpoint emits these events in order:

1. `message_start`
2. `delta`
3. `tool_event`
4. `done`

## Extend the Template

1. Add your domain models under `py/apps/app-template/models/`.
2. Add tool functions under `py/apps/app-template/tools/` and register through `foundrykit.ToolRegistry`.
3. Add MCP tools in `py/mcp/mcp-server-template/tools/`.
4. Replace the sample prompt in `py/apps/app-template/prompts/system.md`.
5. Update Terraform variables in `infra/main.tfvars.example`.

## Deployment

This template uses Terraform through Azure Developer CLI.

```bash
azd provision
azd deploy
```

Use `.env.example` for local development and `.env.azure.example` for cloud settings.

## CI Quality Gates

This repo includes a strict CI workflow at `.github/workflows/ci.yml`.

- Backend: Python lint (`ruff`) + tests (`pytest`)
- Frontend: lint + typecheck + tests + build

To prevent merging code with failing checks, configure branch protection on `main` and require the `CI` workflow status check to pass.