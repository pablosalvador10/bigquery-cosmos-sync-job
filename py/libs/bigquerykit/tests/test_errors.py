import pytest

from ms.fde.bigquerykit.errors import (
    BadRequest,
    BigQueryKitError,
    NotFound,
    PermissionDenied,
    RateLimited,
    map_bigquery_error,
)


class _Exc(Exception):
    def __init__(self, msg: str, *, code: int | None = None, errors: list[dict] | None = None) -> None:
        super().__init__(msg)
        self.code = code
        self.errors = errors or []


@pytest.mark.parametrize(
    ("code", "cls"),
    [(404, NotFound), (400, BadRequest), (403, PermissionDenied), (500, BigQueryKitError)],
)
def test_maps_status_codes(code: int, cls: type) -> None:
    mapped = map_bigquery_error(_Exc("boom", code=code))
    assert isinstance(mapped, cls)


def test_429_becomes_rate_limited() -> None:
    mapped = map_bigquery_error(_Exc("slow down", code=429))
    assert isinstance(mapped, RateLimited)


def test_403_with_rate_limit_reason_becomes_rate_limited() -> None:
    mapped = map_bigquery_error(_Exc("nope", code=403, errors=[{"reason": "rateLimitExceeded"}]))
    assert isinstance(mapped, RateLimited)


def test_403_with_other_reason_stays_permission_denied() -> None:
    mapped = map_bigquery_error(_Exc("denied", code=403))
    assert isinstance(mapped, PermissionDenied)
