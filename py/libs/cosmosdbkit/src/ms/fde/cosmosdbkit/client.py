"""Lifecycle wrapper around ``azure.cosmos.aio.CosmosClient``.

Why this exists:

* Centralises credential resolution so callers don't duplicate the
  key-vs-DefaultAzureCredential branch.
* Provides a single async-context-manager close path that also tears down
  any auto-created ``DefaultAzureCredential``.
* Returns ``CosmosContainer`` wrappers so callers don't touch the raw SDK.
"""

import logging
from typing import Any

from ms.fde.cosmosdbkit.container import CosmosContainer
from ms.fde.cosmosdbkit.credentials import aclose_if_possible, resolve_credential

logger = logging.getLogger(__name__)


class CosmosKitClient:
    """Owns a single ``CosmosClient`` and hands out ``CosmosContainer`` wrappers.

    Use as an async context manager *or* call :meth:`close` explicitly. Reuse a
    single instance per process — constructing ``CosmosClient`` is expensive.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        key: str | None = None,
        credential: Any | None = None,
        client_factory: Any | None = None,
        connection_verify: bool = True,
    ) -> None:
        if not endpoint:
            msg = "Cosmos DB endpoint is required"
            raise ValueError(msg)

        self._endpoint = endpoint
        self._key = key
        self._explicit_credential = credential
        self._client_factory = client_factory  # injection seam for tests
        self._connection_verify = connection_verify
        self._client: Any | None = None
        self._owned_credential: Any | None = None

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def is_open(self) -> bool:
        return self._client is not None

    def _build_client(self) -> Any:
        cred = resolve_credential(key=self._key, credential=self._explicit_credential)
        # We "own" (need to close) the credential only when the caller did not
        # provide one and we did not receive a key.
        if self._key is None and self._explicit_credential is None:
            self._owned_credential = cred

        if self._client_factory is not None:
            return self._client_factory(self._endpoint, cred)

        from azure.cosmos.aio import CosmosClient  # heavy SDK

        kwargs: dict[str, Any] = {}
        if not self._connection_verify:
            kwargs["connection_verify"] = False
        return CosmosClient(url=self._endpoint, credential=cred, **kwargs)

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
            logger.info("CosmosKitClient connected: %s", self._endpoint)
        return self._client

    def get_container(self, database: str, container: str) -> CosmosContainer:
        """Return a ``CosmosContainer`` for a (database, container) pair."""
        if not database or not container:
            msg = "database and container must both be non-empty"
            raise ValueError(msg)
        client = self._ensure_client()
        db = client.get_database_client(database)
        c = db.get_container_client(container)
        return CosmosContainer(c, name=container)

    async def close(self) -> None:
        """Close the underlying ``CosmosClient`` and any owned credentials."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                logger.warning("Error closing CosmosClient", exc_info=True)
            finally:
                self._client = None
        if self._owned_credential is not None:
            await aclose_if_possible(self._owned_credential)
            self._owned_credential = None

    async def __aenter__(self) -> "CosmosKitClient":
        self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()
