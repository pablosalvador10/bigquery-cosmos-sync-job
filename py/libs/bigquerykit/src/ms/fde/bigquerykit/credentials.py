"""Credential resolution for BigQuery.

Three supported modes:

* **Service-account file**: pass ``credentials_path=`` (path to a JSON key file).
* **Service-account info dict**: pass ``credentials_info=`` (parsed JSON dict).
* **Application Default Credentials**: omit both and let ``google.auth.default``
  pick up ``GOOGLE_APPLICATION_CREDENTIALS`` / workload identity / etc.

This module centralises the branching so call sites do not duplicate it.
"""

from typing import Any

_DEFAULT_SCOPES = ("https://www.googleapis.com/auth/bigquery",)


def resolve_credentials(
    *,
    credentials_path: str | None = None,
    credentials_info: dict[str, Any] | None = None,
    credentials: Any | None = None,
    scopes: tuple[str, ...] = _DEFAULT_SCOPES,
) -> tuple[Any | None, str | None]:
    """Resolve BigQuery credentials.

    Returns ``(credentials, project_id)``. ``project_id`` may be ``None`` —
    the caller is responsible for providing it explicitly to the client.

    Precedence: ``credentials`` > ``credentials_info`` > ``credentials_path``
    > Application Default Credentials. Returning ``(None, None)`` lets the
    ``bigquery.Client`` constructor fall back to ADC itself, which is the
    cheapest path in tests.
    """
    if sum(x is not None for x in (credentials, credentials_info, credentials_path)) > 1:
        msg = "Pass at most one of 'credentials', 'credentials_info', 'credentials_path'"
        raise ValueError(msg)

    if credentials is not None:
        return credentials, getattr(credentials, "project_id", None)

    if credentials_info is not None:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=list(scopes))
        return creds, credentials_info.get("project_id")

    if credentials_path is not None:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=list(scopes))
        return creds, getattr(creds, "project_id", None)

    return None, None
