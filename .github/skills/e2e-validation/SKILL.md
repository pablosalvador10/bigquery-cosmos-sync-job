---
name: e2e-validation
description: 'Validates the entire template stack works end-to-end — tests, Docker, infra, health checks. Use after making cross-layer changes, before PRs, or when verifying template integrity.'
argument-hint: 'Optionally specify which layers to validate (e.g., "backend only", "full stack")'
---

## Purpose
Step-by-step validation that every layer of the template works together. Run after any cross-cutting change.

## When to Use
- After modifying multiple layers (backend + infra, libs + app, etc.).
- Before opening a pull request.
- After cloning/forking the template.
- When debugging "it worked before" regressions.

## Flow

### Step 1 — Python workspace installs cleanly
```bash
cd py
uv sync --all-packages
```
**Pass criteria:** No errors. All workspace members resolve.

### Step 2 — All library tests pass
```bash
cd py
uv run pytest libs/ -v
```
**Pass criteria:** 100+ tests, 0 failures. Covers foundrykit, agentkit, evalkit, synthetickit, testkit.

### Step 3 — Backend app tests pass
```bash
cd py
uv run pytest apps/app-template/tests/ -v
```
**Pass criteria:** 3 tests pass (healthz, chat, stream).

### Step 4 — Sample e2e tests pass
```bash
cd py
uv run pytest apps/sample-eval-e2e/tests/ -v
```
**Pass criteria:** 13 tests pass (synthetic generation, evaluation pipeline, end-to-end integration).

### Step 5 — Backend starts and responds
```bash
cd py
uv run uvicorn --app-dir apps/app-template main:app --port 8001 &
sleep 3
curl -s http://localhost:8001/healthz | grep '"ok"'
curl -s -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}' | grep '"response"'
kill %1
```
**Pass criteria:** Health returns `{"status": "ok"}`, chat returns a response with `Summary:`.

### Step 6 — Frontend builds
```bash
cd ts
pnpm install
pnpm --filter ui-copilot-template lint
pnpm --filter ui-copilot-template typecheck
pnpm --filter ui-copilot-template test
pnpm --filter ui-copilot-template build
```
**Pass criteria:** All 4 commands succeed.

### Step 7 — Docker Compose runs
```bash
cp .env.example .env
docker compose up --build -d
sleep 20
curl -s http://localhost:8001/healthz | grep '"ok"'
curl -s http://localhost:5173 | grep -i "html"
docker compose down
```
**Pass criteria:** Backend healthcheck passes, frontend serves HTML.

### Step 8 — Infrastructure validates
```bash
cd infra
terraform init -backend=false
terraform validate
terraform fmt -check -recursive
```
**Pass criteria:** No errors, no formatting drift.

### Step 9 — Python lint passes
```bash
cd py
uv run ruff check .
```
**Pass criteria:** No lint errors.

## Quick Validation (minimum)
If time-constrained, run at least:
```bash
cd py && uv sync --all-packages && uv run pytest libs/ apps/ -v
cd infra && terraform init -backend=false && terraform validate
```
This covers library integrity + infra syntax in ~30 seconds.

## Checklist
- [ ] `uv sync --all-packages` succeeds
- [ ] All library tests pass (102+)
- [ ] Backend app tests pass (3)
- [ ] Sample e2e tests pass (13)
- [ ] Backend healthcheck responds
- [ ] Frontend lint + typecheck + test + build succeeds
- [ ] Docker Compose starts both services
- [ ] Terraform validates
- [ ] Python lint clean
