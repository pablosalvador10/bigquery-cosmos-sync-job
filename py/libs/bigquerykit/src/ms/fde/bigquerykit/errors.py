"""Typed exceptions for bigquerykit.

The google-cloud-bigquery SDK surfaces failures through
``google.api_core.exceptions``. This module maps the few categories we care
about into dedicated types so callers can ``except RateLimited`` instead of
branching on exception classes from the underlying SDK.
"""

from typing import Any


class BigQueryKitError(Exception):
    """Base class for all bigquerykit-raised errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFound(BigQueryKitError):
    """Resource (dataset, table, job) does not exist (HTTP 404)."""


class PermissionDenied(BigQueryKitError):
    """Credentials lack the required IAM permission (HTTP 403)."""


class BadRequest(BigQueryKitError):
    """Invalid query, bad parameter, or schema mismatch (HTTP 400)."""


class RateLimited(BigQueryKitError):
    """Quota or rate limit exceeded (HTTP 429 / 403 ``rateLimitExceeded``)."""

    def __init__(self, message: str, *, retry_after_ms: int = 0) -> None:
        super().__init__(message, status_code=429)
        self.retry_after_ms = retry_after_ms


def _status_of(exc: BaseException) -> int | None:
    code: Any = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    rcode = getattr(response, "status_code", None)
    return rcode if isinstance(rcode, int) else None


def _is_rate_limited(exc: BaseException, status: int | None) -> bool:
    if status == 429:
        return True
    name = exc.__class__.__name__
    if name in {"TooManyRequests", "ResourceExhausted"}:
        return True
    # 403 with reason="rateLimitExceeded" or "quotaExceeded" — common BQ form.
    if status == 403:
        errors = getattr(exc, "errors", None) or []
        for entry in errors:
            reason = (entry or {}).get("reason") if isinstance(entry, dict) else None
            if reason in {"rateLimitExceeded", "quotaExceeded"}:
                return True
    return False


def map_bigquery_error(exc: BaseException) -> BigQueryKitError:
    """Translate a google-api-core / BigQuery exception into a typed error.

    Falls back to a generic ``BigQueryKitError`` when the status is unknown.
    """
    message = str(exc) or exc.__class__.__name__
    status = _status_of(exc)

    if _is_rate_limited(exc, status):
        retry_after_ms = int(getattr(exc, "retry_after_ms", 0) or 0)
        return RateLimited(message, retry_after_ms=retry_after_ms)
    if status == 404 or exc.__class__.__name__ == "NotFound":
        return NotFound(message, status_code=404)
    if status == 403 or exc.__class__.__name__ in {"Forbidden", "PermissionDenied"}:
        return PermissionDenied(message, status_code=403)
    if status == 400 or exc.__class__.__name__ in {"BadRequest", "InvalidArgument"}:
        return BadRequest(message, status_code=400)
    return BigQueryKitError(message, status_code=status)
