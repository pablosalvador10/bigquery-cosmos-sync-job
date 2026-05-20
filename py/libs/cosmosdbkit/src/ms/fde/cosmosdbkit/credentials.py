"""Credential resolution for Cosmos DB.

Two supported modes:

* **Key**: pass a string ``key=`` (the Cosmos primary/secondary key).
* **Managed identity / developer identity**: omit ``key=`` and provide either a
  ready ``credential=`` (any ``azure.core.credentials_async.AsyncTokenCredential``)
  or rely on ``DefaultAzureCredential``.

This module centralizes the branching so call sites do not duplicate it.
"""

from typing import Any, Protocol


class _AsyncCloseable(Protocol):
    async def close(self) -> None: ...


def resolve_credential(
    *,
    key: str | None = None,
    credential: Any | None = None,
) -> Any:
    """Return the credential value to pass into ``CosmosClient(credential=...)``.

    Precedence:
      1. ``key`` — used directly as a string credential.
      2. ``credential`` — used as-is.
      3. ``DefaultAzureCredential`` — constructed lazily.

    ``key`` and ``credential`` are mutually exclusive; passing both raises.
    """
    if key is not None and credential is not None:
        msg = "Pass either 'key' or 'credential', not both"
        raise ValueError(msg)

    if key is not None:
        if not key:
            msg = "Cosmos key must be a non-empty string"
            raise ValueError(msg)
        return key

    if credential is not None:
        return credential

    from azure.identity.aio import DefaultAzureCredential

    return DefaultAzureCredential()


async def aclose_if_possible(obj: Any) -> None:
    """Best-effort async close — used for credentials we built ourselves."""
    close = getattr(obj, "close", None)
    if close is None:
        return
    try:
        result = close()
        if hasattr(result, "__await__"):
            await result
    except Exception:  # noqa: BLE001  # close errors are non-fatal
        return
