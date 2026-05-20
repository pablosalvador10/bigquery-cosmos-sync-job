"""Typed exceptions for cosmosdbkit.

The Azure Cosmos SDK raises ``CosmosHttpResponseError`` for everything; callers
have to inspect ``status_code`` to differentiate. This module maps the few HTTP
status codes we care about into dedicated exception types so callers can
``except NotFound`` instead of branching on ``status_code``.
"""

from typing import Any


class CosmosKitError(Exception):
    """Base class for all cosmosdbkit-raised errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFound(CosmosKitError):
    """Item or resource does not exist (HTTP 404)."""


class Conflict(CosmosKitError):
    """Item already exists or precondition failed (HTTP 409 / 412)."""


class Throttled(CosmosKitError):
    """Request rate too large (HTTP 429). Carries the SDK-suggested retry delay."""

    def __init__(self, message: str, *, retry_after_ms: int = 0) -> None:
        super().__init__(message, status_code=429)
        self.retry_after_ms = retry_after_ms


def map_cosmos_error(exc: BaseException) -> CosmosKitError:
    """Translate an Azure Cosmos SDK exception into a typed cosmosdbkit error.

    Falls back to a generic ``CosmosKitError`` when the status code is unknown.
    """
    status: Any = getattr(exc, "status_code", None)
    message = str(exc) or exc.__class__.__name__

    if status == 404:
        return NotFound(message, status_code=404)
    if status in (409, 412):
        return Conflict(message, status_code=status)
    if status == 429:
        retry_after_ms = int(getattr(exc, "retry_after_ms", 0) or 0)
        return Throttled(message, retry_after_ms=retry_after_ms)
    return CosmosKitError(message, status_code=status if isinstance(status, int) else None)
