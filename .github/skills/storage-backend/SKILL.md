---
name: storage-backend
description: 'Adds a new storage backend implementing the Storage protocol. Use when adding a database, cache, or persistence layer beyond InMemory and Cosmos DB.'
argument-hint: 'Describe the storage backend (e.g., "Redis cache", "PostgreSQL", "Azure Blob Storage")'
---

## Purpose
Step-by-step workflow for adding a new storage backend that implements the `Storage` protocol.

## When to Use
- Adding a new database backend (PostgreSQL, Redis, SQLite, etc.).
- Replacing or extending the existing storage options.
- Adding a caching layer in front of existing storage.

## Flow

1. **Review the Storage protocol** in `py/apps/app-template/services/storage.py`:
   ```python
   class Storage(Protocol):
       async def add_message(self, message: StoredMessage) -> StoredMessage: ...
       async def list_messages(self, session_id: str) -> list[StoredMessage]: ...
   ```
   Your backend must implement both methods with these exact signatures.

2. **Create the implementation** in `services/storage.py` (or a new file imported there):
   - Class name: `{Backend}Storage` (e.g., `RedisStorage`, `PostgresStorage`).
   - Constructor: accept config from `AppSettings`. Validate required settings.
   - `add_message()`: persist and return the `StoredMessage`.
   - `list_messages()`: query by `session_id` and return list of `StoredMessage`.
   - Use async clients. Never block the event loop.
   - Use parameterized queries — never interpolate user input.

3. **Add configuration** to `py/apps/app-template/core/config.py`:
   - Add new settings fields to `AppSettings` (e.g., `redis_url: str = ""`).
   - Add the new mode to `storage_mode: Literal["inmemory", "cosmos", "redis"]`.

4. **Wire into factory** — update `get_storage()`:
   ```python
   def get_storage() -> Storage:
       global _storage
       if _storage is None:
           if settings.storage_mode == "inmemory":
               _storage = InMemoryStorage()
           elif settings.storage_mode == "cosmos":
               _storage = CosmosStorage()
           elif settings.storage_mode == "redis":
               _storage = RedisStorage()
       return _storage
   ```

5. **Update environment files**:
   - Add new env vars to `.env.example` and `.env.azure.example`.
   - Document the new `STORAGE_MODE` value.

6. **Write tests**:
   - Test `add_message` → `list_messages` round-trip.
   - Test empty session returns empty list.
   - Test session isolation (messages from one session don't leak to another).

7. **Infrastructure** (if cloud-hosted):
   - Add resource to `infra/modules/core/main.tf` via `add-azure-resource` skill.

## Checklist
- [ ] Implements `Storage` protocol (both methods, correct signatures)
- [ ] Uses async I/O
- [ ] Uses parameterized queries (no string interpolation)
- [ ] Config added to `AppSettings`
- [ ] Factory updated in `get_storage()`
- [ ] Environment files updated
- [ ] Tests pass for round-trip and isolation
