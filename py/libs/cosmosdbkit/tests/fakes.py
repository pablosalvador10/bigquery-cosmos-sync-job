"""In-memory fakes used by cosmosdbkit tests.

These mimic the *async* Azure Cosmos SDK surface that ``CosmosContainer`` and
``CosmosKitClient`` actually call:

* ``ContainerClient.upsert_item / create_item / replace_item / delete_item / read_item``
* ``ContainerClient.query_items`` (async iterator)
* ``ContainerClient.read_all_items`` (async iterator)
* ``DatabaseClient.get_container_client``
* ``CosmosClient.get_database_client`` / ``close``
"""

from collections.abc import AsyncIterator
from typing import Any


class FakeCosmosError(Exception):
    """Mirrors ``azure.cosmos.exceptions.CosmosHttpResponseError``."""

    def __init__(self, *, status_code: int, message: str = "", retry_after_ms: int = 0) -> None:
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code
        self.retry_after_ms = retry_after_ms


class FakeContainer:
    """Minimal in-memory async container.

    Items are keyed by ``(partition_key, id)``. Partition key path is
    ``/<partition_field>`` — defaults to ``/id`` (matches the ``hackathons``
    container partition strategy).
    """

    def __init__(self, name: str = "fake", *, partition_field: str = "id") -> None:
        self.id = name
        self._items: dict[tuple[str, str], dict[str, Any]] = {}
        self._partition_field = partition_field
        self.calls: list[tuple[str, dict[str, Any]]] = []

    # ------------------------------------------------------------------ writes

    async def upsert_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("upsert_item", {"body": body, **kwargs}))
        pk = str(body[self._partition_field])
        self._items[(pk, body["id"])] = dict(body)
        return dict(body)

    async def create_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create_item", {"body": body, **kwargs}))
        pk = str(body[self._partition_field])
        if (pk, body["id"]) in self._items:
            raise FakeCosmosError(status_code=409, message="already exists")
        self._items[(pk, body["id"])] = dict(body)
        return dict(body)

    async def replace_item(self, item: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("replace_item", {"item": item, "body": body, **kwargs}))
        pk = str(body[self._partition_field])
        if (pk, item) not in self._items:
            raise FakeCosmosError(status_code=404, message="not found")
        self._items[(pk, item)] = dict(body)
        return dict(body)

    async def delete_item(self, item: str, partition_key: str, **kwargs: Any) -> None:
        self.calls.append(("delete_item", {"item": item, "partition_key": partition_key, **kwargs}))
        key = (str(partition_key), item)
        if key not in self._items:
            raise FakeCosmosError(status_code=404, message="not found")
        del self._items[key]

    # ------------------------------------------------------------------- reads

    async def read_item(self, item: str, partition_key: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("read_item", {"item": item, "partition_key": partition_key, **kwargs}))
        key = (str(partition_key), item)
        if key not in self._items:
            raise FakeCosmosError(status_code=404, message="not found")
        return dict(self._items[key])

    def query_items(
        self,
        *,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        self.calls.append(("query_items", {"query": query, "parameters": parameters, **kwargs}))
        return _async_iter(self._matching(query, parameters or [], kwargs.get("partition_key")))

    def read_all_items(self, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        self.calls.append(("read_all_items", dict(kwargs)))
        pk = kwargs.get("partition_key")
        items = [dict(v) for k, v in self._items.items() if pk is None or k[0] == str(pk)]
        return _async_iter(items)

    # -------------------------------------------------------------- internals

    def _matching(
        self,
        query: str,
        parameters: list[dict[str, Any]],
        partition_key: Any | None,
    ) -> list[dict[str, Any]]:
        # The fake supports a tiny query language sufficient for tests:
        #   - "SELECT * FROM c" returns everything
        #   - "WHERE c.<field> = @p" filters by exact match
        #   - "VALUE COUNT(1)" returns a single integer row
        params = {p["name"]: p["value"] for p in parameters}
        rows = [
            dict(v) for k, v in self._items.items() if partition_key is None or k[0] == str(partition_key)
        ]
        # filter
        wl = query.lower()
        if " where " in wl:
            where = query.split(" WHERE ", 1)[1] if " WHERE " in query else query.split(" where ", 1)[1]
            # split by AND
            for clause in where.split(" AND "):
                clause = clause.strip().rstrip(";")
                if "=" not in clause:
                    continue
                left, right = (s.strip() for s in clause.split("=", 1))
                # left like c.field, right like @p
                field = left.split(".", 1)[1] if "." in left else left
                value = params.get(right, right)
                rows = [r for r in rows if r.get(field) == value]
        if "value count(1)" in wl:
            return [{"_v": len(rows)}]
        if " order by " in wl:
            seg = (
                query.split(" ORDER BY ", 1)[1] if " ORDER BY " in query else query.split(" order by ", 1)[1]
            )
            tokens = seg.strip().split()
            field = tokens[0].split(".", 1)[1] if "." in tokens[0] else tokens[0]
            reverse = len(tokens) > 1 and tokens[1].upper() == "DESC"
            rows.sort(key=lambda r: r.get(field, 0), reverse=reverse)
        return rows


class FakeDatabase:
    def __init__(self, containers: dict[str, FakeContainer]) -> None:
        self._containers = containers

    def get_container_client(self, name: str) -> FakeContainer:
        if name not in self._containers:
            self._containers[name] = FakeContainer(name=name)
        return self._containers[name]


class FakeCosmosClient:
    """Stand-in for ``azure.cosmos.aio.CosmosClient``."""

    def __init__(
        self,
        endpoint: str = "https://example",
        credential: Any = "key",
        databases: dict[str, FakeDatabase] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.credential = credential
        self._databases = databases or {}
        self.closed = False

    def get_database_client(self, name: str) -> FakeDatabase:
        if name not in self._databases:
            self._databases[name] = FakeDatabase({})
        return self._databases[name]

    async def close(self) -> None:
        self.closed = True


async def _async_iter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class ThrottlingContainer(FakeContainer):
    """Container that throws 429 a fixed number of times before succeeding."""

    def __init__(self, *, throttle_count: int, retry_after_ms: int = 50) -> None:
        super().__init__(name="throttle")
        self._remaining = throttle_count
        self._retry_after_ms = retry_after_ms

    async def read_item(self, item: str, partition_key: str, **kwargs: Any) -> dict[str, Any]:
        if self._remaining > 0:
            self._remaining -= 1
            raise FakeCosmosError(status_code=429, message="throttled", retry_after_ms=self._retry_after_ms)
        return await super().read_item(item, partition_key, **kwargs)
