"""Tests for the typed error mapping."""

import pytest

from ms.fde.cosmosdbkit.errors import Conflict, CosmosKitError, NotFound, Throttled, map_cosmos_error
from tests.fakes import FakeCosmosError


def test_not_found_inherits_from_cosmoskit_error() -> None:
    assert issubclass(NotFound, CosmosKitError)


def test_conflict_inherits_from_cosmoskit_error() -> None:
    assert issubclass(Conflict, CosmosKitError)


def test_throttled_inherits_from_cosmoskit_error() -> None:
    assert issubclass(Throttled, CosmosKitError)


def test_throttled_carries_retry_after_ms() -> None:
    err = Throttled("rate limited", retry_after_ms=125)
    assert err.retry_after_ms == 125
    assert err.status_code == 429


def test_map_404_returns_not_found() -> None:
    sdk_exc = FakeCosmosError(status_code=404)
    mapped = map_cosmos_error(sdk_exc)
    assert isinstance(mapped, NotFound)
    assert mapped.status_code == 404


def test_map_409_returns_conflict() -> None:
    sdk_exc = FakeCosmosError(status_code=409)
    mapped = map_cosmos_error(sdk_exc)
    assert isinstance(mapped, Conflict)
    assert mapped.status_code == 409


def test_map_412_returns_conflict() -> None:
    mapped = map_cosmos_error(FakeCosmosError(status_code=412))
    assert isinstance(mapped, Conflict)


def test_map_429_returns_throttled_with_retry_after() -> None:
    mapped = map_cosmos_error(FakeCosmosError(status_code=429, retry_after_ms=200))
    assert isinstance(mapped, Throttled)
    assert mapped.retry_after_ms == 200


def test_map_unknown_status_returns_base_error() -> None:
    mapped = map_cosmos_error(FakeCosmosError(status_code=500))
    assert type(mapped) is CosmosKitError
    assert mapped.status_code == 500


def test_map_exception_without_status_code_uses_none() -> None:
    mapped = map_cosmos_error(RuntimeError("boom"))
    assert type(mapped) is CosmosKitError
    assert mapped.status_code is None


def test_cosmoskit_error_message_preserved() -> None:
    mapped = map_cosmos_error(FakeCosmosError(status_code=404, message="missing item"))
    assert "missing item" in str(mapped)


def test_throttled_default_retry_after_is_zero() -> None:
    err = Throttled("x")
    assert err.retry_after_ms == 0


def test_raise_and_catch_as_base() -> None:
    with pytest.raises(CosmosKitError):
        raise NotFound("x")
