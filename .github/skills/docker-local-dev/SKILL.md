---
name: docker-local-dev
description: 'Runs the full stack locally with Docker Compose. Use when starting local development, running docker compose, debugging containers, or testing the full application locally.'
argument-hint: 'Optionally specify which services to run or debug'
---

## Purpose
Exact commands for running the full application stack locally using Docker Compose.

## When to Use
- Starting local end-to-end development.
- Testing backend + frontend together.
- Debugging container build or runtime issues.

## Flow

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Default .env works for local dev (STORAGE_MODE=inmemory, OTEL_EXPORTER=console)
   ```

2. **Build and start all services**:
   ```bash
   docker compose up --build
   ```
   This starts:
   - **backend** on `http://localhost:8001` (FastAPI with healthcheck)
   - **frontend** on `http://localhost:5173` (React via nginx)

3. **Verify health**:
   ```bash
   # Backend health (waits for container healthcheck to pass)
   curl http://localhost:8001/healthz
   # Expected: {"status": "ok"}

   # Frontend loads
   open http://localhost:5173
   ```

4. **View logs**:
   ```bash
   # All services
   docker compose logs -f

   # Backend only
   docker compose logs -f backend

   # Frontend only
   docker compose logs -f frontend
   ```

5. **Rebuild after changes**:
   ```bash
   # Rebuild specific service
   docker compose up --build backend

   # Full rebuild
   docker compose down && docker compose up --build
   ```

6. **Stop**:
   ```bash
   docker compose down
   ```

## Alternative: Run Without Docker

**Backend** (direct):
```bash
cd py/apps/app-template
uv pip install -e .[dev]
uv run uvicorn main:app --reload --port 8001
```

**Frontend** (direct):
```bash
cd ts
pnpm install
pnpm --filter ui-copilot-template dev
```

## Troubleshooting
- **Port conflict**: Change `API_PORT` in `.env` or update `docker-compose.yml` port mapping.
- **Backend won't start**: Check `.env` is present and has required vars.
- **Frontend can't reach backend**: Verify `CORS_ORIGINS` includes frontend URL. Check nginx proxy config.
- **Healthcheck fails**: Backend needs 15-30s to start. Check `docker compose logs backend`.

## Checklist
- [ ] `.env` file exists (copied from `.env.example`)
- [ ] `docker compose up --build` succeeds
- [ ] Backend healthcheck passes
- [ ] Frontend loads in browser
- [ ] Chat sends message and receives streamed response
