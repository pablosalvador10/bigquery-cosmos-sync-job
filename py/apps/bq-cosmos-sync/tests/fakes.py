"""Shared test fakes — in-process replacements for BigQuery + Cosmos I/O."""

from collections.abc import AsyncIterator
from typing import Any

from ms.fde.cosmosdbkit.errors import NotFound


class FakeBigQueryReader:
    """Pretends to be ``BigQueryReader`` — yields canned pages."""

    def __init__(self, pages_by_query_prefix: dict[str, list[list[dict[str, Any]]]]) -> None:
        # Match the first SQL line stripped — keep test fixtures small.
        self._pages = pages_by_query_prefix
        self.received_queries: list[str] = []

    async def __aenter__(self) -> "FakeBigQueryReader":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def close(self) -> None:
        pass

    async def query_rows(
        self,
        sql: str,
        *,
        parameters: list[Any] | None = None,
        page_size: int = 1000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        del parameters, page_size
        self.received_queries.append(sql)
        pages = self._pick(sql)
        for page in pages:
            yield list(page)

    def _pick(self, sql: str) -> list[list[dict[str, Any]]]:
        for prefix, pages in self._pages.items():
            if prefix in sql:
                return pages
        return []


class FakeCosmosContainer:
    """In-memory partition-aware Cosmos container."""

    def __init__(self, *, name: str = "fake") -> None:
        self.name = name
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.upsert_calls = 0
        # When set, the next ``upsert_item`` raises (then resets to None).
        self.raise_next: Exception | None = None

    async def upsert_item(self, body: dict[str, Any], **_: Any) -> dict[str, Any]:
        self.upsert_calls += 1
        if self.raise_next is not None:
            exc, self.raise_next = self.raise_next, None
            raise exc
        pk_field = _detect_pk_field(body)
        key = (str(body["id"]), str(body[pk_field]))
        self.items[key] = dict(body)
        return dict(body)

    async def try_read_item(self, item: str, partition_key: str, **_: Any) -> dict[str, Any] | None:
        return self.items.get((item, partition_key))

    async def read_item(self, item: str, partition_key: str, **_: Any) -> dict[str, Any]:
        v = self.items.get((item, partition_key))
        if v is None:
            raise NotFound(f"{item} not found")
        return v


def _detect_pk_field(body: dict[str, Any]) -> str:
    # Best-effort: take the first scalar field other than ``id``.
    for k, v in body.items():
        if k == "id":
            continue
        if isinstance(v, (str, int, float, bool)):
            return k
    msg = "Cannot detect partition key field in fake document"
    raise ValueError(msg)
