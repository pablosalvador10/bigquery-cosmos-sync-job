"""Async wrapper around a BigQuery dataset.

``BigQueryDataset`` exposes the dataset-scoped operations actually used in this
repository: parameterized queries (paged, streamed), table existence checks,
basic table create / load helpers. It is structurally similar to
:class:`ms.fde.cosmosdbkit.CosmosContainer` so that the BQ → Cosmos sync app
can rely on a uniform mental model across both SDKs.

Implementation notes:

* The wrapper takes a ``bigquery.Client`` as a constructor argument rather than
  building it itself. This makes the class trivially testable with an in-memory
  fake — no monkeypatching of ``google.cloud.bigquery`` required.
* All SDK exceptions go through ``map_bigquery_error`` so callers see typed
  bigquerykit errors.
* The blocking SDK calls run inside ``asyncio.to_thread``.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from ms.fde.bigquerykit.errors import map_bigquery_error


class BigQueryDataset:
    """High-level async wrapper around a single BigQuery dataset.

    Construct via :meth:`BigQueryKitClient.get_dataset` rather than directly.
    """

    def __init__(self, client: Any, *, project: str, dataset: str) -> None:
        if not project or not dataset:
            msg = "project and dataset must both be non-empty"
            raise ValueError(msg)
        self._client = client
        self._project = project
        self._dataset = dataset

    @property
    def project(self) -> str:
        return self._project

    @property
    def name(self) -> str:
        return self._dataset

    @property
    def reference(self) -> str:
        """Fully-qualified ``project.dataset`` reference for use in SQL backticks."""
        return f"{self._project}.{self._dataset}"

    def table_ref(self, table: str) -> str:
        """Return ``project.dataset.table`` — safe to embed in SQL backticks."""
        if not table:
            msg = "table must be a non-empty string"
            raise ValueError(msg)
        return f"{self._project}.{self._dataset}.{table}"

    # ------------------------------------------------------------------ queries

    async def query_rows(
        self,
        sql: str,
        *,
        parameters: list[Any] | dict[str, Any] | None = None,
        page_size: int = 1000,
        job_config: Any | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Run ``sql`` and yield rows as ``list[dict]`` pages."""
        if page_size <= 0:
            msg = "page_size must be positive"
            raise ValueError(msg)

        from ms.fde.bigquerykit.client import _coerce_parameters

        params = _coerce_parameters(parameters)

        def _submit() -> Any:
            from google.cloud.bigquery import QueryJobConfig

            cfg = job_config or QueryJobConfig()
            if params:
                cfg.query_parameters = params
            return self._client.query(sql, job_config=cfg)

        try:
            job = await asyncio.to_thread(_submit)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc

        def _start_pages() -> Any:
            result = job.result(timeout=timeout, page_size=page_size)
            return iter(result.pages)

        try:
            pages = await asyncio.to_thread(_start_pages)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc

        _SENTINEL = object()

        while True:
            try:
                page = await asyncio.to_thread(_next_page, pages, _SENTINEL)
            except Exception as exc:
                raise map_bigquery_error(exc) from exc
            if page is _SENTINEL:
                return

            rows = [dict(row.items()) for row in page]
            if not rows:
                continue
            yield rows

    async def query_one(
        self,
        sql: str,
        *,
        parameters: list[Any] | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Return the first row of ``sql``, or ``None``."""
        async for page in self.query_rows(sql, parameters=parameters, page_size=1, timeout=timeout):
            if page:
                return page[0]
        return None

    async def query_all(
        self,
        sql: str,
        *,
        parameters: list[Any] | dict[str, Any] | None = None,
        max_rows: int | None = None,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Materialize a query into a list, optionally capped at ``max_rows``.

        ``max_rows`` is a client-side cap; pair with ``LIMIT`` in SQL when
        possible to bound server-side work.
        """
        if max_rows is not None and max_rows <= 0:
            msg = "max_rows must be positive"
            raise ValueError(msg)

        out: list[dict[str, Any]] = []
        async for page in self.query_rows(
            sql, parameters=parameters, page_size=max(max_rows or 1000, 1), timeout=timeout
        ):
            for row in page:
                out.append(row)
                if max_rows is not None and len(out) >= max_rows:
                    return out
        return out

    async def count(
        self,
        table: str,
        *,
        where: str | None = None,
        parameters: list[Any] | dict[str, Any] | None = None,
    ) -> int:
        """Return ``COUNT(*)`` for a table, optionally filtered by a ``WHERE`` clause."""
        sql = f"SELECT COUNT(*) AS n FROM `{self.table_ref(table)}`"
        if where:
            sql = f"{sql} WHERE {where}"
        row = await self.query_one(sql, parameters=parameters)
        return int((row or {}).get("n", 0))

    # ----------------------------------------------------------------- tables

    async def exists_table(self, table: str) -> bool:
        """Return ``True`` if ``table`` exists in this dataset."""
        from google.api_core.exceptions import NotFound as _GoogleNotFound

        def _check() -> bool:
            try:
                self._client.get_table(self.table_ref(table))
                return True
            except _GoogleNotFound:
                return False

        try:
            return await asyncio.to_thread(_check)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc

    async def create_table(
        self,
        table: str,
        *,
        schema: list[Any],
        exists_ok: bool = True,
        partitioning_field: str | None = None,
    ) -> None:
        """Create ``table`` from a schema list. Optionally day-partition by a column."""

        def _create() -> None:
            from google.cloud.bigquery import (
                Table,
                TimePartitioning,
                TimePartitioningType,
            )

            tbl = Table(self.table_ref(table), schema=schema)
            if partitioning_field:
                tbl.time_partitioning = TimePartitioning(
                    type_=TimePartitioningType.DAY,
                    field=partitioning_field,
                )
            self._client.create_table(tbl, exists_ok=exists_ok)

        try:
            await asyncio.to_thread(_create)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc

    async def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Stream-insert ``rows`` into ``table``. Raises if any row is rejected."""
        if not rows:
            return

        def _insert() -> list[dict[str, Any]]:
            return self._client.insert_rows_json(self.table_ref(table), rows)

        try:
            errors = await asyncio.to_thread(_insert)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc

        if errors:
            from ms.fde.bigquerykit.errors import BadRequest

            msg = f"insert_rows rejected {len(errors)} row(s): {errors[:3]!r}"
            raise BadRequest(msg)


def _next_page(pages: Any, sentinel: Any) -> Any:
    return next(pages, sentinel)
