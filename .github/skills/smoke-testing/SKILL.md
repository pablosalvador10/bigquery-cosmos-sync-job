---
name: smoke-testing
description: 'Confirms deployability and basic system health after deployment or container start. Use after azd deploy, docker compose up, or any deployment to verify the system is alive.'
argument-hint: 'Specify target environment (e.g., "local Docker", "Azure staging")'
---

## Purpose
Minimal confidence checks that the system is alive and functional after deployment. Not exhaustive — just enough to confirm nothing is fundamentally broken.

## When to Use
- After `azd deploy` to Azure.
- After `docker compose up --build`.
- After container image updates.
- As post-deployment CI gate.

## Flow

### Step 1 — Backend health
```bash
# Local
curl -sf http://localhost:8001/healthz | jq .

# Azure (replace with deployed URL)
curl -sf https://<backend-url>/healthz | jq .
```
**Pass:** Returns `{"status": "ok"}` with HTTP 200.

### Step 2 — Sync chat round-trip
```bash
curl -sf -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "smoke test"}' | jq .
```
**Pass:** Returns JSON with `session_id`, `message_id`, and non-empty `response`.

### Step 3 — SSE streaming works
```bash
curl -sN -X POST http://localhost:8001/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "smoke test"}' | head -20
```
**Pass:** Output contains `event: message_start`, `event: delta`, and `event: done`.

### Step 4 — Frontend loads
```bash
# Local
curl -sf http://localhost:5173 | grep -i "<html"

# Azure
curl -sf https://<frontend-url> | grep -i "<html"
```
**Pass:** Returns HTML content.

### Step 5 — Storage connectivity (if Cosmos enabled)
```bash
curl -sf -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "persistence check", "session_id": "smoke-test-session"}' | jq .session_id
```
**Pass:** Returns the same `session_id` sent in the request. No 500 errors in backend logs.

### Step 6 — Telemetry emitting (optional)
```bash
# Check backend logs for structured output
docker compose logs backend 2>&1 | grep "chat_stream_complete"
```
**Pass:** Structured log entries appear with expected fields.

## Automated Smoke Script
```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8001}"
FRONTEND_URL="${2:-http://localhost:5173}"

echo "=== Smoke Tests ==="

echo -n "Health check... "
curl -sf "$BASE_URL/healthz" | grep -q '"ok"' && echo "PASS" || { echo "FAIL"; exit 1; }

echo -n "Chat endpoint... "
curl -sf -X POST "$BASE_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "smoke"}' | grep -q '"response"' && echo "PASS" || { echo "FAIL"; exit 1; }

echo -n "SSE streaming... "
STREAM=$(curl -sN -X POST "$BASE_URL/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "smoke"}' --max-time 10 2>/dev/null || true)
echo "$STREAM" | grep -q "event: done" && echo "PASS" || { echo "FAIL"; exit 1; }

echo -n "Frontend loads... "
curl -sf "$FRONTEND_URL" | grep -qi "html" && echo "PASS" || { echo "FAIL"; exit 1; }

echo "=== All Smoke Tests Passed ==="
```

## Checklist
- [ ] Backend `/healthz` returns 200
- [ ] Chat endpoint returns valid response
- [ ] SSE stream emits all 4 event types
- [ ] Frontend serves HTML
- [ ] No 500 errors in backend logs
- [ ] Storage writes succeed (if Cosmos enabled)
