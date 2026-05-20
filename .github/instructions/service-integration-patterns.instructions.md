---
description: "Patterns for integrating external services, APIs, and Azure resources into the application. Use when connecting to a new service (Service Bus, Redis, BigQuery, external APIs), creating mock/fake implementations for testing, or following the protocol-first abstraction pattern."
applyTo: 'py/**'
---

# External Service Integration Patterns

## Protocol-First Pattern

When integrating any external service, follow the same pattern used by `Storage` in `services/storage.py`:

### 1. Define a Protocol (interface)
```python
from typing import Protocol

class NotificationService(Protocol):
    async def send(self, recipient: str, message: str) -> bool: ...
    async def list_sent(self, recipient: str) -> list[dict]: ...
```

### 2. Build an in-memory fake (for local dev + tests)
```python
from collections import defaultdict

class InMemoryNotificationService:
    def __init__(self) -> None:
        self._sent: dict[str, list[dict]] = defaultdict(list)

    async def send(self, recipient: str, message: str) -> bool:
        self._sent[recipient].append({"message": message})
        return True

    async def list_sent(self, recipient: str) -> list[dict]:
        return self._sent.get(recipient, [])
```

### 3. Build the real implementation
```python
class AzureServiceBusNotificationService:
    def __init__(self) -> None:
        self._client = ServiceBusClient(
            fully_qualified_namespace=settings.servicebus_namespace,
            credential=DefaultAzureCredential(),
        )
    async def send(self, recipient: str, message: str) -> bool:
        ...
```

### 4. Wire via factory + config
```python
_service: NotificationService | None = None

def get_notification_service() -> NotificationService:
    global _service
    if _service is None:
        if settings.notification_mode == "inmemory":
            _service = InMemoryNotificationService()
        else:
            _service = AzureServiceBusNotificationService()
    return _service
```

Add `notification_mode` to `AppSettings` and both `.env.example` files.

## External API Integration

When connecting to a third-party or internal API (BigQuery, CRM, analytics):

1. **Create a client class** in `services/` — wrap `httpx.AsyncClient` with typed methods.
2. **Configure via `AppSettings`** — base URL, API keys, timeouts. Never hardcode.
3. **Add a fake client** returning canned responses for tests.
4. **Use factory pattern** to switch between real and fake via env var.
5. **Handle errors explicitly** — timeouts, 4xx, 5xx → return structured error dict, don't raise into the agent.

```python
class BigQueryClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self._api_key = api_key

    async def query(self, sql: str) -> list[dict]:
        response = await self._client.post("/query", json={"sql": sql},
            headers={"Authorization": f"Bearer {self._api_key}"})
        response.raise_for_status()
        return response.json()["rows"]
```

## Mock API Server (when the real service doesn't exist yet)

When building against an API that isn't ready:

1. Add mock route in `py/mcp/mcp-server-template/server.py` or a new FastAPI app.
2. Return realistic canned responses matching the expected schema.
3. Add to `docker-compose.yml` as a separate service.
4. Point the client config at the mock URL for local dev.

```yaml
# docker-compose.yml
mock-api:
  build: ./py/mcp/mcp-server-template
  ports:
    - "8082:8080"
```

## Azure Service Client Pattern

For any Azure service (Service Bus, Redis, Key Vault, AKS, Event Hubs):

1. **Terraform**: Provision via `add-azure-resource` skill.
2. **SDK client**: Create singleton-like client following `FoundryClient` pattern:
   - Constructor takes settings
   - Lazy-init the SDK client
   - Cache via module-level factory function
3. **Auth**: Use `DefaultAzureCredential` (dev) or `ManagedIdentityCredential` (production).
4. **Protocol + fake**: Always have an in-memory fake for local dev and CI.
5. **Config**: Add to `AppSettings` → `.env.example` → `.env.azure.example`.

## CI/CD Rules

When adding any external service integration:

- **Tests must pass without the real service** — `conftest.py` forces in-memory/fake mode.
- **CI runs with fakes only** — no cloud credentials in CI environment.
- **Mark integration tests** with `@pytest.mark.integration` if they need real services:
  ```python
  @pytest.mark.integration
  async def test_real_servicebus():
      """Requires SERVICEBUS_NAMESPACE env var."""
      ...
  ```
- **CI workflow** (`ci.yml`) runs unit tests by default. Integration tests run separately (e.g., nightly or on-demand).
- **Keep `docker compose up` working** with just fakes — no mandatory cloud dependencies.
