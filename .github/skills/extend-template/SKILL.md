---
name: extend-template
description: 'Guides forking and customizing this template for a new project. Use when starting a new project from this template, cloning the template, or adapting it for a specific domain.'
argument-hint: 'Describe the target application (e.g., "HR assistant with document search", "IoT dashboard with device management")'
---

## Purpose
Step-by-step guide for creating a new application from this template repository.

## When to Use
- Starting a new agentic AI project based on this template.
- Adapting the template for a specific domain or use case.
- Onboarding a team to the template.

## Flow

1. **Clone and rename**:
   ```bash
   gh repo create my-org/my-agent-app --template pablosalvador10/template-agentic-ai-apps-azure
   cd my-agent-app
   ```

2. **Update project identity**:
   - `py/pyproject.toml`: change `name`.
   - `py/apps/app-template/pyproject.toml`: change `name` and `description`.
   - `ts/apps/ui-copilot-template/package.json`: change `name`.
   - `azure.yaml`: update service names.
   - `README.md`: rewrite for your project.

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Update APP_NAME, AZURE_FOUNDRY_PROJECT_ENDPOINT, model name
   ```

4. **Customize the agent**:
   - Edit system prompt in `py/apps/app-template/prompts/system.md`.
   - Create YAML agent spec (follow `agent-authoring` skill).
   - Define domain-specific tools (follow `tool-registration` skill).

5. **Add domain tools**:
   - Create tool files in `py/apps/app-template/tools/`.
   - Register with `@registry.register`.
   - Add tool names to agent YAML spec.

6. **Extend the data layer** (if needed):
   - Add new Pydantic models in `models/`.
   - Add new storage methods or backends (follow `storage-backend` skill).
   - Add Cosmos DB containers (follow `cosmos-db-patterns` skill).

7. **Customize the UI**:
   - Update `ts/apps/ui-copilot-template/src/App.tsx` branding.
   - Add domain-specific components (follow `add-chat-feature` skill).
   - Update styles in `styles.css`.

8. **Update infrastructure**:
   - Adjust `infra/variables.tf` defaults for your project.
   - Add Azure resources if needed (follow `add-azure-resource` skill).

9. **Test and deploy**:
   - Run tests: `cd py/apps/app-template && uv run pytest tests/ -v`.
   - Local: `docker compose up --build` (follow `docker-local-dev` skill).
   - Azure: `azd provision && azd deploy` (follow `azure-deployment` skill).

10. **Customize Copilot instructions** (optional):
    - Update `.github/copilot-instructions.md` with project-specific rules.
    - Add domain-specific instruction files in `.github/instructions/`.
    - Add project-specific skills in `.github/skills/`.

## What to Keep vs. Customize

| Keep As-Is | Customize |
|------------|-----------|
| `py/libs/foundrykit` (Foundry abstractions) | `py/apps/app-template/tools/` (your domain tools) |
| `py/libs/agentkit` (agent loader) | `py/apps/app-template/prompts/` (your prompts) |
| SSE streaming contract | `py/apps/app-template/models/` (your data models) |
| Storage protocol pattern | `infra/variables.tf` (your resource config) |
| Docker + Terraform structure | `ts/apps/*/src/` (your UI components) |

## Checklist
- [ ] Project names updated across configs
- [ ] System prompt customized for domain
- [ ] Domain tools registered
- [ ] `.env` configured
- [ ] Tests pass
- [ ] Local dev works (`docker compose up`)
- [ ] Deployed to Azure (if ready)
