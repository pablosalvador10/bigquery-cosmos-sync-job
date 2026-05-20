"""Lifecycle wrapper around ``google.cloud.bigquery.Client``.

Why this exists:

* Centralises credential resolution so callers don't duplicate the
  service-account-vs-ADC branch.
* Wraps the synchronous SDK in async methods backed by ``asyncio.to_thread`` so
  callers in async applications get a uniform interface — mirroring
  :mod:`ms.fde.cosmosdbkit`.
* Returns :class:`BigQueryDataset` wrappers so callers don't touch the raw SDK.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Iterable
from typing import Any

from ms.fde.bigquerykit.credentials import resolve_credentials
from ms.fde.bigquerykit.dataset import BigQueryDataset
from ms.fde.bigquerykit.errors import map_bigquery_error

logger = logging.getLogger(__name__)


class BigQueryKitClient:
    """Owns a single ``bigquery.Client`` and hands out :class:`BigQueryDataset` wrappers.

    Reuse a single instance per process; constructing the SDK ``Client`` is
    expensive and authenticates eagerly.
    """

    def __init__(
        self,
        *,
        project: str,
        location: str = "US",
        credentials_path: str | None = None,
        credentials_info: dict[str, Any] | None = None,
        credentials: Any | None = None,
        client_factory: Any | None = None,
    ) -> None:
        if not project:
            msg = "BigQuery project is required"
            raise ValueError(msg)

        self._project = project
        self._location = location
        self._credentials_path = credentials_path
        self._credentials_info = credentials_info
        self._explicit_credential = credentials
        self._client_factory = client_factory  # injection seam for tests
        self._client: Any | None = None

    # ---- properties ---------------------------------------------------------

    @property
    def project(self) -> str:
        return self._project

    @property
    def location(self) -> str:
        return self._location

    @property
    def is_open(self) -> bool:
        return self._client is not None

    # ---- lifecycle ----------------------------------------------------------

    def _build_client(self) -> Any:
        creds, _ = resolve_credentials(
            credentials_path=self._credentials_path,
            credentials_info=self._credentials_info,
            credentials=self._explicit_credential,
        )

        if self._client_factory is not None:
            return self._client_factory(self._project, creds, self._location)

        from google.cloud.bigquery import Client  # heavy SDK

        return Client(project=self._project, credentials=creds, location=self._location)

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
            logger.info("BigQueryKitClient connected: project=%s", self._project)
        return self._client

    def get_dataset(self, dataset: str) -> BigQueryDataset:
        """Return a :class:`BigQueryDataset` for ``project.dataset``."""
        if not dataset:
            msg = "dataset must be a non-empty string"
            raise ValueError(msg)
        client = self._ensure_client()
        return BigQueryDataset(client, project=self._project, dataset=dataset)

    async def close(self) -> None:
        """Close the underlying SDK client. Idempotent."""
        if self._client is None:
            return
        client, self._client = self._client, None
        close = getattr(client, "close", None)
        if close is None:
            return
        try:
            await asyncio.to_thread(close)
        except Exception:  # noqa: BLE001
            logger.warning("Error closing BigQuery client", exc_info=True)

    async def __aenter__(self) -> "BigQueryKitClient":
        self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    # ---- queries ------------------------------------------------------------

    async def query_rows(
        self,
        sql: str,
        *,
        parameters: list[Any] | dict[str, Any] | None = None,
        page_size: int = 1000,
        job_config: Any | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Execute ``sql`` and yield rows as ``list[dict]`` pages.

        ``parameters`` may be either a list of already-built
        ``ScalarQueryParameter`` / ``ArrayQueryParameter`` objects, or a dict
        of ``{name: value}`` which is converted via :func:`to_query_parameters`.
        """
        dataset_proxy = BigQueryDataset(self._ensure_client(), project=self._project, dataset="_")
        async for page in dataset_proxy.query_rows(
            sql,
            parameters=parameters,
            page_size=page_size,
            job_config=job_config,
            timeout=timeout,
        ):
            yield page

    async def execute(
        self,
        sql: str,
        *,
        parameters: list[Any] | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> int:
        """Run a DDL/DML statement and return ``num_dml_affected_rows``."""
        client = self._ensure_client()
        params = _coerce_parameters(parameters)

        def _run() -> int:
            from google.cloud.bigquery import QueryJobConfig

            job = client.query(sql, job_config=QueryJobConfig(query_parameters=params))
            job.result(timeout=timeout)
            return int(getattr(job, "num_dml_affected_rows", 0) or 0)

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            raise map_bigquery_error(exc) from exc


def _coerce_parameters(
    parameters: list[Any] | dict[str, Any] | None,
) -> list[Any]:
    if parameters is None:
        return []
    if isinstance(parameters, dict):
        from ms.fde.bigquerykit.query import QueryBuilder

        qb = QueryBuilder("SELECT 1")
        for k, v in parameters.items():
            if isinstance(v, (list, tuple)):
                qb.bind_array(k, list(v))
            else:
                qb.bind(k, v)
        return qb.build()[1]
    if isinstance(parameters, Iterable):
        return list(parameters)
    msg = f"Unsupported parameters type: {type(parameters).__name__}"
    raise TypeError(msg)
