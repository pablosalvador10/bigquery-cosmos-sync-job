"""In-memory Cosmos DB container fake with partition key and ETag simulation."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any
from uuid import uuid4


class FakeCosmosContainer:
    """Dict-backed Cosmos DB container for tests.

    Supports partition key enforcement, ETag-based optimistic concurrency,
    and parameter-based query matching.

    Args:
        partition_key: Partition key path (e.g. ``"/session_id"``).
    """

    def __init__(self, partition_key: str = "/id") -> None:
        self._partition_key = partition_key.lstrip("/")
        self._items: dict[str, dict[str, Any]] = {}
        self._etag_counter = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f'"{self._etag_counter}"'

    def _item_key(self, item_id: str, partition_value: str | None = None) -> str:
        return f"{partition_value or '_'}:{item_id}"

    async def create_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Insert a new item. Raises if the item already exists."""
        item = dict(body)
        if "id" not in item:
            item["id"] = str(uuid4())
        pk = item.get(self._partition_key, item["id"])
        key = self._item_key(item["id"], str(pk))
        if key in self._items:
            raise ValueError(f"Item already exists: {item['id']}")
        item["_etag"] = self._next_etag()
        self._items[key] = item
        return item

    async def read_item(
        self,
        item: str,
        partition_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Read a single item by ID and partition key."""
        key = self._item_key(item, partition_key)
        if key not in self._items:
            raise KeyError(f"Item not found: {item}")
        return self._items[key]

    async def upsert_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Insert or replace an item."""
        item = dict(body)
        if "id" not in item:
            item["id"] = str(uuid4())
        pk = item.get(self._partition_key, item["id"])
        key = self._item_key(item["id"], str(pk))
        item["_etag"] = self._next_etag()
        self._items[key] = item
        return item

    async def replace_item(
        self,
        item: str,
        body: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Replace an existing item. Supports If-Match ETag checks."""
        pk = body.get(self._partition_key, body.get("id", item))
        key = self._item_key(item, str(pk))
        if key not in self._items:
            raise KeyError(f"Item not found: {item}")

        # Optimistic concurrency via If-Match header.
        headers = kwargs.get("headers", {})
        if_match = headers.get("If-Match")
        if if_match and self._items[key].get("_etag") != if_match:
            raise ValueError("ETag mismatch — item was modified concurrently")

        updated = dict(body)
        updated["_etag"] = self._next_etag()
        self._items[key] = updated
        return updated

    async def delete_item(
        self,
        item: str,
        partition_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Delete an item by ID and partition key."""
        key = self._item_key(item, partition_key)
        if key not in self._items:
            raise KeyError(f"Item not found: {item}")
        del self._items[key]

    def query_items(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> "_AsyncItemIterator":
        """Query items using parameter-based matching.

        Does NOT parse full SQL — matches items by checking parameter
        values against item fields. This covers the common pattern::

            SELECT * FROM c WHERE c.field = @value
        """
        param_map: dict[str, Any] = {}
        if parameters:
            for p in parameters:
                name = p.get("name", "").lstrip("@")
                param_map[name] = p.get("value")

        matched = []
        for item in self._items.values():
            if self._matches(item, param_map):
                matched.append(item)

        return _AsyncItemIterator(matched)

    @staticmethod
    def _matches(item: dict[str, Any], params: dict[str, Any]) -> bool:
        """Check if an item matches all query parameters."""
        if not params:
            return True
        return all(item.get(k) == v for k, v in params.items())

    # ── Convenience helpers for tests ────────────────────────────── #

    def seed(self, *items: dict[str, Any]) -> "FakeCosmosContainer":
        """Synchronously seed items into the container for test setup."""
        for body in items:
            item = dict(body)
            if "id" not in item:
                item["id"] = str(uuid4())
            pk = item.get(self._partition_key, item["id"])
            key = self._item_key(item["id"], str(pk))
            item["_etag"] = self._next_etag()
            self._items[key] = item
        return self

    @property
    def all_items(self) -> list[dict[str, Any]]:
        """Return all items in the container (for test assertions)."""
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)


class _AsyncItemIterator:
    """Async iterator over query results to match the Cosmos SDK API."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> "_AsyncItemIterator":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item
