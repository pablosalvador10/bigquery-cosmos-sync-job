---
name: troubleshooting
description: 'Diagnoses and fixes common errors in the agentic app template. Use when debugging failures, fixing broken agent flows, resolving SSE streaming issues, troubleshooting Cosmos DB connections, or diagnosing deployment errors.'
argument-hint: 'Describe the error or symptom (e.g., "agent returns empty response", "SSE stream stops", "Cosmos connection refused")'
---

## Purpose
Diagnosis and fix guide for common errors across backend, frontend, infrastructure, and agent execution.

## When to Use
- An endpoint returns an error or unexpected response.
- SSE streaming breaks or stops mid-stream.
- Agent execution fails or returns empty.
- Storage or database connection errors.
- Docker or deployment failures.

## Diagnosis Flow

1. **Identify the layer**:
   - Backend API error (4xx/5xx) → check logs, Pydantic validation, route wiring.
   - SSE stream incomplete → check `_stream_reply()` generator, frontend parser.
   - Agent error → check credentials, agent spec, tool registration.
   - Storage error → check `STORAGE_MODE`, Cosmos credentials, partition key.
   - Infrastructure error → check Terraform state, `azd` output, Container App logs.

2. **Check logs**:
   ```bash
   # Backend logs (Docker)
   docker compose logs -f backend

   # Backend logs (direct)
   # structlog outputs to stdout — look for error-level entries
   ```

3. **Run targeted tests**:
   ```bash
   cd py/apps/app-template && uv run python -m pytest tests/ -v
   ```

## Common Issues

### Agent returns empty response
- **Cause**: `AZURE_FOUNDRY_PROJECT_ENDPOINT` not set → app falls back to simulation.
- **Fix**: Set the endpoint in `.env` or verify with `echo $AZURE_FOUNDRY_PROJECT_ENDPOINT`.
- **Cause**: Agent spec YAML has wrong tool names → tools don't bind.
- **Fix**: Verify tool names in `agents/chat-agent.yaml` match `@registry.register` function names exactly.

### `ModuleNotFoundError: No module named 'foundrykit'`
- **Cause**: Dependencies not installed in the uv workspace.
- **Fix**: `cd py && uv sync`

### SSE stream stops without `done` event
- **Cause**: Exception in `_stream_reply()` generator before `done` is yielded.
- **Fix**: Check backend logs for the traceback. Wrap agent calls in try/except.
- **Cause**: Frontend aborts the request (timeout or navigation).
- **Fix**: Check browser DevTools Network tab for aborted requests.

### Cosmos DB connection refused
- **Cause**: `COSMOS_ENDPOINT` not set or wrong when `STORAGE_MODE=cosmos`.
- **Fix**: Verify `.env` has correct `COSMOS_ENDPOINT`. For local dev, use `STORAGE_MODE=inmemory`.
- **Cause**: Missing RBAC role assignment for managed identity.
- **Fix**: Ensure `Cosmos DB Built-in Data Contributor` role is assigned in Terraform.

### Docker healthcheck fails
- **Cause**: Backend takes too long to start.
- **Fix**: Increase healthcheck `start_period` in `docker-compose.yml` or check for import errors.

### `terraform validate` fails
- **Cause**: Missing provider or variable.
- **Fix**: Run `terraform init -backend=false` first. Check `variables.tf` for missing required vars.

### Frontend can't reach backend
- **Cause**: CORS not configured for frontend origin.
- **Fix**: Set `CORS_ORIGINS=http://localhost:5173` in `.env`.
- **Cause**: Backend not running or wrong port.
- **Fix**: Verify backend is healthy: `curl http://localhost:8001/healthz`

### `DefaultAzureCredential` authentication failed
- **Cause**: Not signed in to Azure CLI.
- **Fix**: Run `az login` and retry.
- **Cause**: Using managed_identity mode locally.
- **Fix**: Set `FOUNDRY_CREDENTIAL_MODE=dev` in `.env` for local development.

## Debugging Checklist
- [ ] Backend `/healthz` returns `{"status": "ok"}`
- [ ] `.env` file exists and has correct values
- [ ] `uv sync` has been run (dependencies installed)
- [ ] Tests pass: `uv run python -m pytest tests/ -v`
- [ ] For agent mode: `AZURE_FOUNDRY_PROJECT_ENDPOINT` is set and valid
- [ ] For Cosmos: `STORAGE_MODE=cosmos` and `COSMOS_ENDPOINT` are set
- [ ] For Azure: `az login` is active and subscription is correct
