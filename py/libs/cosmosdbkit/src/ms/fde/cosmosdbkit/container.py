"""Async wrapper around an Azure Cosmos container client.

``CosmosContainer`` exposes the operations actually used in this repository:
single-item reads/writes plus parameterized queries. It is structurally
compatible with the ``ContainerProxy`` protocol used inside
``py/apps/platform`` (so existing services can swap in a ``CosmosContainer``).

Implementation notes:

* The wrapper takes the SDK ``container_client`` as a constructor argument
  rather than building it itself. This makes the class trivially testable with
  an in-memory fake — no monkeypatching of ``azure.cosmos.aio`` required.
* All SDK exceptions go through ``map_cosmos_error`` so callers see typed
  cosmosdbkit errors.
"""

from collections.abc import AsyncIterator
from typing import Any

from ms.fde.cosmosdbkit.errors import CosmosKitError, NotFound, map_cosmos_error
from ms.fde.cosmosdbkit.query import normalize_parameters


class CosmosContainer:
    """High-level async wrapper around a single Cosmos container.

    Compatible with ``ContainerProxy`` from ``py/apps/platform/src/storage/protocol.py``.
    """

    def __init__(self, container_client: Any, *, name: str | None = None) -> None:
        self._c = container_client
        self._name = name or getattr(container_client, "id", "<unknown>")

    @property
    def name(self) -> str:
        return self._name

    # ------------------------------------------------------------------ writes

    async def upsert_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Insert or replace an item by id."""
        try:
            return await self._c.upsert_item(body=body, **kwargs)
        except Exception as exc:
            raise map_cosmos_error(exc) from exc

    async def create_item(self, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Insert an item; raises ``Conflict`` if id already exists."""
        try:
            return await self._c.create_item(body=body, **kwargs)
        except Exception as exc:
            raise map_cosmos_error(exc) from exc

    async def replace_item(self, item: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Replace an existing item; raises ``NotFound`` if missing."""
        try:
            return await self._c.replace_item(item=item, body=body, **kwargs)
        except Exception as exc:
            raise map_cosmos_error(exc) from exc

    async def delete_item(self, item: str, partition_key: str, **kwargs: Any) -> None:
        """Delete by id + partition key. ``NotFound`` is swallowed."""
        try:
            await self._c.delete_item(item=item, partition_key=partition_key, **kwargs)
        except Exception as exc:
            mapped = map_cosmos_error(exc)
            if isinstance(mapped, NotFound):
                return
            raise mapped from exc

    # ------------------------------------------------------------------- reads

    async def read_item(self, item: str, partition_key: str, **kwargs: Any) -> dict[str, Any]:
        """Read a single item by id + partition key. Raises ``NotFound``."""
        try:
            return await self._c.read_item(item=item, partition_key=partition_key, **kwargs)
        except Exception as exc:
            raise map_cosmos_error(exc) from exc

    async def try_read_item(self, item: str, partition_key: str, **kwargs: Any) -> dict[str, Any] | None:
        """Like ``read_item`` but returns ``None`` instead of raising ``NotFound``."""
        try:
            return await self.read_item(item, partition_key, **kwargs)
        except NotFound:
            return None

    # --------------------------------------------------------------- iteration

    def query_items(
        self,
        query: str,
        parameters: list[dict[str, Any]] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream items matching a parameterized query.

        ``ContainerProxy``-compatible signature; returns the SDK's async
        iterator directly so it can be consumed with ``async for``.
        """
        params = normalize_parameters(parameters)
        return self._c.query_items(query=query, parameters=params, **kwargs)

    def read_all_items(self, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        """Stream every item in the container."""
        return self._c.read_all_items(**kwargs)

    # ------------------------------------------------------------- convenience

    async def query_one(
        self,
        query: str,
        parameters: list[dict[str, Any]] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Return the first item matched by a query, or ``None``."""
        async for item in self.query_items(query, parameters, **kwargs):
            return item
        return None

    async def query_all(
        self,
        query: str,
        parameters: list[dict[str, Any]] | dict[str, Any] | None = None,
        *,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Materialize a query into a list, optionally capped at ``max_items``.

        ``max_items`` must be a positive int when provided. The cap is
        client-side; pair with SQL ``TOP`` / ``OFFSET LIMIT`` for server-side
        bounds when possible.
        """
        if max_items is not None and max_items <= 0:
            msg = "max_items must be positive"
            raise ValueError(msg)

        out: list[dict[str, Any]] = []
        try:
            async for item in self.query_items(query, parameters, **kwargs):
                out.append(item)
                if max_items is not None and len(out) >= max_items:
                    break
        except CosmosKitError:
            raise
        except Exception as exc:
            raise map_cosmos_error(exc) from exc
        return out

    async def count(
        self,
        query: str,
        parameters: list[dict[str, Any]] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> int:
        """Run a ``SELECT VALUE COUNT(1) ...`` style query and return the scalar.

        The provided query MUST yield a single numeric value per result row
        (typical: ``SELECT VALUE COUNT(1) FROM c WHERE ...``).
        """
        total = 0
        first = True
        async for value in self.query_items(query, parameters, **kwargs):
            if isinstance(value, (int, float)):
                total += int(value)
                first = False
                continue
            if isinstance(value, dict) and len(value) == 1:
                only = next(iter(value.values()))
                if isinstance(only, (int, float)):
                    total += int(only)
                    first = False
                    continue
            msg = f"count() expected scalar rows, got {value!r}"
            raise CosmosKitError(msg)
        if first:
            return 0
        return total
