---
name: load-testing
description: 'Validates performance and concurrency behavior of backend endpoints. Use when preparing for production, checking latency under load, or verifying system stability.'
argument-hint: 'Describe the target endpoint or scenario (e.g., "chat endpoint under 50 concurrent users")'
---

## Purpose
Step-by-step guide for load testing the template backend to validate performance before production deployment.

## When to Use
- Before first production deployment.
- After significant backend changes (new endpoints, storage changes).
- When validating Cosmos DB performance under load.
- When establishing performance baselines.

## Flow

### Step 1 — Identify target flows
Map the user-critical paths to endpoints:

| Flow | Endpoint | Method | Expected Latency |
|------|----------|--------|------------------|
| Health check | `/healthz` | GET | < 50ms |
| Sync chat | `/api/v1/chat` | POST | < 2s |
| Streaming chat | `/api/v1/chat/stream` | POST | TTFB < 500ms |

### Step 2 — Create test scenarios
Create a load test script using a tool like `hey`, `k6`, or `locust`:

**Using `hey` (simple HTTP benchmarking):**
```bash
# Install: brew install hey (macOS) or go install github.com/rakyll/hey@latest

# Baseline: health endpoint
hey -n 1000 -c 50 http://localhost:8001/healthz

# Chat endpoint under load
hey -n 200 -c 20 -m POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize this text for me please"}' \
  http://localhost:8001/api/v1/chat
```

**Using Python + httpx (for streaming validation):**
```python
"""Load test for SSE streaming endpoint."""
import asyncio
import time
import httpx

async def stream_chat(client: httpx.AsyncClient, i: int) -> dict:
    start = time.monotonic()
    payload = {"message": f"Load test message {i}"}
    first_byte = None
    async with client.stream("POST", "/api/v1/chat/stream", json=payload) as resp:
        async for chunk in resp.aiter_text():
            if first_byte is None:
                first_byte = time.monotonic() - start
    total = time.monotonic() - start
    return {"request": i, "ttfb_ms": first_byte * 1000, "total_ms": total * 1000}

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        tasks = [stream_chat(client, i) for i in range(50)]
        results = await asyncio.gather(*tasks)
    ttfbs = [r["ttfb_ms"] for r in results]
    totals = [r["total_ms"] for r in results]
    print(f"TTFB  — p50: {sorted(ttfbs)[25]:.0f}ms, p99: {sorted(ttfbs)[49]:.0f}ms")
    print(f"Total — p50: {sorted(totals)[25]:.0f}ms, p99: {sorted(totals)[49]:.0f}ms")

asyncio.run(main())
```

### Step 3 — Define pass/fail thresholds

| Metric | Target | Fail |
|--------|--------|------|
| Health p99 latency | < 100ms | > 500ms |
| Chat p99 latency | < 3s | > 10s |
| Stream TTFB p99 | < 1s | > 5s |
| Error rate | < 1% | > 5% |
| Concurrent users | 50+ | Crashes at < 10 |

### Step 4 — Run against target environment
```bash
# Local
docker compose up --build -d
# ... run load tests against localhost:8001 ...

# Azure (after deployment)
# ... run load tests against deployed backend URL ...
```

### Step 5 — Analyze results
- Check p50, p95, p99 latencies.
- Check error rate and error types (429s, 500s, timeouts).
- Check Container App scaling behavior (if in Azure).
- Review Application Insights for slow dependencies.

## Decision Logic
- **InMemory storage**: Fastest — baselines for pure API performance.
- **Cosmos storage**: Real bottleneck — test with `STORAGE_MODE=cosmos` for production-representative results.
- **With agent calls**: Slowest — Foundry API latency dominates. Focus on TTFB for streaming.

## Checklist
- [ ] Target endpoints and flows identified
- [ ] Load test tool installed and configured
- [ ] Thresholds defined before running
- [ ] Tests run against both local and Azure environments
- [ ] Results compared against thresholds
- [ ] Bottlenecks identified and documented
