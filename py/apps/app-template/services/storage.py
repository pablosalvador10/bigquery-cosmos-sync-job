"""Storage protocol and implementations for message persistence."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Protocol

from core.config import settings
from models.chat import StoredMessage

if TYPE_CHECKING:
    from azure.cosmos.aio import CosmosClient


class Storage(Protocol):
    """Abstract storage interface for message persistence."""

    async def add_message(self, message: StoredMessage) -> StoredMessage: ...

    async def list_messages(self, session_id: str) -> list[StoredMessage]: ...


class InMemoryStorage:
    """Dict-backed storage for local development."""

    def __init__(self) -> None:
        self._messages: dict[str, list[StoredMessage]] = defaultdict(list)

    async def add_message(self, message: StoredMessage) -> StoredMessage:
        self._messages[message.session_id].append(message)
        return message

    async def list_messages(self, session_id: str) -> list[StoredMessage]:
        return self._messages.get(session_id, [])


class CosmosStorage:
    """Azure Cosmos DB storage backend using Entra ID authentication."""

    def __init__(self) -> None:
        if not settings.cosmos_endpoint:
            raise ValueError("COSMOS_ENDPOINT must be set when STORAGE_MODE=cosmos")

        from azure.cosmos.aio import CosmosClient
        from azure.identity import DefaultAzureCredential

        self._client: CosmosClient = CosmosClient(
            url=settings.cosmos_endpoint,
            credential=DefaultAzureCredential(),
        )
        self._database_name = settings.cosmos_database_name
        self._container_name = settings.cosmos_container_messages

    async def add_message(self, message: StoredMessage) -> StoredMessage:
        db = self._client.get_database_client(self._database_name)
        container = db.get_container_client(self._container_name)
        await container.upsert_item(message.model_dump())
        return message

    async def list_messages(self, session_id: str) -> list[StoredMessage]:
        db = self._client.get_database_client(self._database_name)
        container = db.get_container_client(self._container_name)
        query = "SELECT * FROM c WHERE c.session_id = @session_id"
        items = container.query_items(
            query=query,
            parameters=[{"name": "@session_id", "value": session_id}],
            enable_cross_partition_query=False,
        )
        return [StoredMessage.model_validate(item) async for item in items]


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = InMemoryStorage() if settings.storage_mode == "inmemory" else CosmosStorage()
    return _storage
