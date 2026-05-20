# Setup

## Prerequisites
- Python 3.11+
- Node 20+
- [`uv`](https://docs.astral.sh/uv/) (Python workspace manager)
- [`pnpm`](https://pnpm.io/) (Node package manager)
- Docker (optional, for local E2E)
- Terraform + Azure CLI + azd (for cloud deploy)

## Backend

```bash
cd py
uv sync --all-packages          # Install all workspace packages + dev deps
uv run uvicorn --app-dir apps/app-template main:app --reload --port 8001
```

## Run Tests

```bash
cd py
uv run pytest libs/ apps/app-template/tests/ apps/sample-eval-e2e/tests/ -v
```

## Frontend

```bash
cd ts
pnpm install
pnpm --filter ui-copilot-template dev
```

## Local E2E (Docker)

```bash
cp .env.example .env             # Only needed on first run
docker compose up --build
```

Backend: http://localhost:8001 | Frontend: http://localhost:5173

## Validate Everything

```bash
# Backend health
curl http://localhost:8001/healthz

# All Python tests (libs + apps)
cd py && uv run pytest libs/ apps/ -v

# Frontend lint + typecheck + tests + build
cd ts && pnpm --filter ui-copilot-template lint && \
  pnpm --filter ui-copilot-template typecheck && \
  pnpm --filter ui-copilot-template test && \
  pnpm --filter ui-copilot-template build

# Infrastructure validation
cd infra && terraform init -backend=false && terraform validate && terraform fmt -check -recursive
```

## Cloud Deployment

```bash
cp .env.azure.example .env.azure   # Fill in real values
cp infra/main.tfvars.example infra/main.tfvars  # Set subscription, region
azd provision
azd deploy
```
