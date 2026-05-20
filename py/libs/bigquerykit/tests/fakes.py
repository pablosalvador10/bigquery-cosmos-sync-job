"""In-memory fakes used across bigquerykit tests."""

from typing import Any


class _FakeRow:
    """Minimal stand-in for ``google.cloud.bigquery.Row`` — only ``items()`` is used."""

    def __init__(self, mapping: dict[str, Any]) -> None:
        self._m = mapping

    def items(self) -> list[tuple[str, Any]]:
        return list(self._m.items())


class _FakeRowIterator:
    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self.pages = [[_FakeRow(r) for r in page] for page in pages]

    def __iter__(self) -> Any:
        for page in self.pages:
            yield from page


class _FakeResult:
    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self._pages = pages
        self.iterator = _FakeRowIterator(pages)

    @property
    def pages(self) -> Any:
        return iter(self.iterator.pages)


class _FakeJob:
    def __init__(self, pages: list[list[dict[str, Any]]], *, dml_rows: int = 0) -> None:
        self._pages = pages
        self._dml_rows = dml_rows
        self.num_dml_affected_rows = dml_rows

    def result(self, *, timeout: float | None = None, page_size: int | None = None) -> _FakeResult:
        del timeout, page_size
        return _FakeResult(self._pages)


class FakeBigQueryClient:
    """In-memory replacement for ``google.cloud.bigquery.Client``."""

    def __init__(
        self,
        *,
        pages_by_sql_substring: dict[str, list[list[dict[str, Any]]]] | None = None,
        existing_tables: set[str] | None = None,
        dml_rows: int = 0,
        raise_on_query: Exception | None = None,
        raise_on_create_table: Exception | None = None,
    ) -> None:
        self._pages = pages_by_sql_substring or {}
        self._existing_tables = set(existing_tables or [])
        self._dml_rows = dml_rows
        self._raise_on_query = raise_on_query
        self._raise_on_create_table = raise_on_create_table

        self.received_sql: list[str] = []
        self.created_tables: list[Any] = []
        self.inserted: dict[str, list[dict[str, Any]]] = {}
        self.closed = False

    # ---- query ----
    def query(self, sql: str, job_config: Any | None = None) -> _FakeJob:
        if self._raise_on_query is not None:
            raise self._raise_on_query
        self.received_sql.append(sql)
        pages = self._lookup(sql)
        return _FakeJob(pages, dml_rows=self._dml_rows)

    def _lookup(self, sql: str) -> list[list[dict[str, Any]]]:
        for needle, pages in self._pages.items():
            if needle in sql:
                return pages
        return []

    # ---- tables ----
    def get_table(self, ref: str) -> Any:
        if ref in self._existing_tables:
            return object()
        from google.api_core.exceptions import NotFound as _GNF

        raise _GNF(f"{ref} not found")

    def create_table(self, table: Any, exists_ok: bool = True) -> Any:
        if self._raise_on_create_table is not None:
            raise self._raise_on_create_table
        self.created_tables.append(table)
        return table

    def insert_rows_json(self, ref: str, rows: list[dict[str, Any]]) -> list[Any]:
        self.inserted.setdefault(ref, []).extend(rows)
        return []

    # ---- lifecycle ----
    def close(self) -> None:
        self.closed = True
