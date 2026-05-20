---
description: "Docker containerization and Azure Container Apps deployment patterns. Use when writing Dockerfiles, adding services to docker-compose, deploying containers to Azure Container Apps, or designing microservice architecture."
applyTo: '**/Dockerfile,**/docker-compose.yml,infra/**'
---

# Docker & Container Apps Patterns

## Dockerfile Conventions

### Python Backend (FastAPI)
Follow the existing pattern in `py/apps/app-template/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml /app/
RUN uv pip install --system -e .
COPY . /app
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Rules:
- Use `python:3.12-slim` (not full image — reduces size).
- Install only production dependencies — dev deps go in optional extras.
- Copy `pyproject.toml` first and install deps before copying code (layer caching).
- Expose the port matching `API_PORT` in settings.
- Health endpoint at `/healthz` for container orchestration probes.

### Frontend (React + nginx)
Follow the existing pattern in `ts/apps/ui-copilot-template/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json tsconfig.json vite.config.ts eslint.config.js index.html /app/
COPY src /app/src
RUN npm install && npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Rules:
- Multi-stage build: build in node, serve from nginx.
- nginx config handles API reverse proxy to backend.
- Static assets served from `/usr/share/nginx/html`.

### MCP Server
Same pattern as backend — FastAPI app in `python:3.12-slim`.

## docker-compose.yml Conventions

### Existing Services
```yaml
services:
  backend:     # FastAPI on :8001, healthcheck at /healthz
  frontend:    # nginx on :5173 (mapped to :80 in container), depends on backend
```

### Adding a New Service
```yaml
services:
  # ... existing services ...
  my-worker:
    build:
      context: ./py/apps/my-worker
      dockerfile: Dockerfile
    container_name: my-worker
    env_file:
      - .env.example
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "8002:8002"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/healthz"]
      interval: 15s
      timeout: 5s
      retries: 5
```

Rules:
- Every service gets a healthcheck.
- Use `depends_on` with `condition: service_healthy` for ordering.
- Load env from `.env.example` for local dev.
- Use `container_name` for predictable log/debug references.

## Azure Container Apps Deployment

### How docker-compose maps to Container Apps
| docker-compose | Azure Container Apps |
|----------------|---------------------|
| `services.backend` | Container App `backend` in Container App Environment |
| `services.frontend` | Container App `frontend` in Container App Environment |
| `ports` | Ingress configuration (external/internal) |
| `env_file` | Container App environment variables (from Terraform outputs) |
| `healthcheck` | Container App health probes |
| `depends_on` | No equivalent — use retry logic + health probes |

### Terraform Pattern for Container Apps
See `infra/modules/core/main.tf` for existing resource definitions.

When adding a new Container App:
1. Add `azurerm_container_app` resource in `modules/core/main.tf`.
2. Configure ingress (external for public-facing, internal for service-to-service).
3. Set environment variables from Terraform outputs/variables.
4. Add health probe matching `/healthz` endpoint.
5. Wire container image from `backend_image`/`frontend_image` variables.

### Container App Ingress
```hcl
ingress {
  target_port      = 8001
  external_enabled = true   # true for public, false for internal
  transport        = "auto"
}
```

### Scaling
```hcl
min_replicas = 0  # Scale to zero when idle (cost saving)
max_replicas = 10 # Scale up under load
```

### Health Probes
```hcl
liveness_probe {
  path      = "/healthz"
  port      = 8001
  transport = "HTTP"
}
```

## Best Practices
- **One process per container** — don't run both backend and frontend in one container.
- **No secrets in Dockerfiles** — use env vars or Azure Key Vault.
- **Layer caching** — copy dependency files first, install, then copy source code.
- **Multi-stage builds** — compile in a build stage, copy to slim runtime stage.
- **Health endpoints** — every service must expose `/healthz`.
- **Stateless containers** — use Cosmos DB or external storage, not local filesystem.
- **Logging to stdout** — structlog outputs to stdout, Container Apps captures automatically.
