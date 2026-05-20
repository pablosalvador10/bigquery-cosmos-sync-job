---
description: Monorepo layout, library organization, workspace setup. Use when adding new libraries, apps, or packages, or when deciding where code should live.
---

# Monorepo Structure

## Workspace Managers
- **Python**: `uv` workspace. Root config at `py/pyproject.toml`. Members: `apps/app-template`, `libs/foundrykit`, `libs/agentkit`, `mcp/mcp-server-template`.
- **TypeScript**: `pnpm` workspace. Root config at `ts/package.json` + `ts/pnpm-workspace.yaml`. Members: `apps/ui-copilot-template`.

## Where Code Lives

| Location | What Goes Here | Rule |
|----------|---------------|------|
| `py/libs/foundrykit` | Azure AI Foundry abstractions (client, agent manager, tool registry, config) | Domain-neutral. No app-specific logic. |
| `py/libs/agentkit` | YAML-driven agent spec loading | Domain-neutral. No Azure SDK imports. |
| `py/apps/app-template` | FastAPI app — routes, models, services, tools, tests | Domain logic here. Depends on libs. |
| `py/mcp/mcp-server-template` | MCP HTTP server skeleton | Standalone. Own dependencies. |
| `ts/apps/ui-copilot-template` | React chat UI | Frontend only. API-driven, no backend imports. |
| `infra/` | Terraform modules + azd config | No app code. Variable-driven. |

## Dependency Direction
- `apps/` → `libs/` (allowed)
- `libs/` → `libs/` (allowed if explicit)
- `libs/` → `apps/` (NEVER — breaks reusability)
- `apps/` → `apps/` (NEVER — no cross-app imports)

## Adding a New Library
1. Create `py/libs/{name}/` with `pyproject.toml` and `{name}/` package directory.
2. Add to `py/pyproject.toml` workspace members: `"libs/{name}"`.
3. Add as dependency in consuming app's `pyproject.toml`: `{name} = { workspace = true }`.

## Adding a New App
1. Create under `py/apps/{name}/` or `ts/apps/{name}/`.
2. Add to workspace members in root config.
3. Add Dockerfile if containerized.
4. Add service entry in `docker-compose.yml` and `azure.yaml` if deployed.
