"""Tests for credential resolution."""

import pytest

from ms.fde.cosmosdbkit.credentials import aclose_if_possible, resolve_credential


def test_key_takes_precedence_when_only_key_passed() -> None:
    assert resolve_credential(key="abc") == "abc"


def test_credential_passed_through_when_key_absent() -> None:
    sentinel = object()
    assert resolve_credential(credential=sentinel) is sentinel


def test_passing_both_key_and_credential_raises() -> None:
    with pytest.raises(ValueError, match="either"):
        resolve_credential(key="abc", credential=object())


def test_empty_key_raises() -> None:
    with pytest.raises(ValueError):
        resolve_credential(key="")


def test_default_azure_credential_used_when_nothing_provided() -> None:
    cred = resolve_credential()
    # We don't import DefaultAzureCredential at module load; check duck-typing.
    assert hasattr(cred, "get_token") or hasattr(cred, "close")


@pytest.mark.asyncio
async def test_aclose_handles_object_without_close() -> None:
    await aclose_if_possible(object())  # must not raise


@pytest.mark.asyncio
async def test_aclose_calls_async_close() -> None:
    closed: list[bool] = []

    class C:
        async def close(self) -> None:
            closed.append(True)

    await aclose_if_possible(C())
    assert closed == [True]


@pytest.mark.asyncio
async def test_aclose_calls_sync_close() -> None:
    closed: list[bool] = []

    class C:
        def close(self) -> None:
            closed.append(True)

    await aclose_if_possible(C())
    assert closed == [True]


@pytest.mark.asyncio
async def test_aclose_swallows_close_errors() -> None:
    class C:
        async def close(self) -> None:
            raise RuntimeError("boom")

    await aclose_if_possible(C())  # must not raise
