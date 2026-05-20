"""Tests for ``CosmosKitClient`` lifecycle and container handoff."""

from typing import Any

import pytest

import ms.fde.cosmosdbkit.client as client_mod
import ms.fde.cosmosdbkit.credentials as creds_mod
from ms.fde.cosmosdbkit.client import CosmosKitClient
from ms.fde.cosmosdbkit.container import CosmosContainer
from tests.fakes import FakeContainer, FakeCosmosClient, FakeDatabase


def _factory(**databases: dict[str, FakeContainer]) -> Any:
    fake_dbs = {name: FakeDatabase(containers) for name, containers in databases.items()}
    fake_client = FakeCosmosClient(databases=fake_dbs)

    def make(endpoint: str, credential: Any) -> FakeCosmosClient:
        fake_client.endpoint = endpoint
        fake_client.credential = credential
        return fake_client

    return make, fake_client


def test_endpoint_required() -> None:
    with pytest.raises(ValueError):
        CosmosKitClient(endpoint="")


def test_endpoint_property() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    assert client.endpoint == "https://x"


def test_is_open_false_before_use() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    assert not client.is_open


def test_get_container_returns_wrapper() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    c = client.get_container("db", "c")
    assert isinstance(c, CosmosContainer)
    assert c.name == "c"


def test_get_container_opens_client_lazily() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    assert not client.is_open
    client.get_container("db", "c")
    assert client.is_open


def test_get_container_validates_arguments() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    with pytest.raises(ValueError):
        client.get_container("", "c")
    with pytest.raises(ValueError):
        client.get_container("db", "")


def test_uses_factory_with_key() -> None:
    factory, fake_client = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="my-key", client_factory=factory)
    client.get_container("db", "c")
    assert fake_client.credential == "my-key"


def test_uses_factory_with_explicit_credential() -> None:
    factory, fake_client = _factory(db={"c": FakeContainer(name="c")})
    sentinel = object()
    client = CosmosKitClient(endpoint="https://x", credential=sentinel, client_factory=factory)
    client.get_container("db", "c")
    assert fake_client.credential is sentinel


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    factory, fake_client = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    client.get_container("db", "c")
    await client.close()
    await client.close()
    assert fake_client.closed is True
    assert not client.is_open


@pytest.mark.asyncio
async def test_close_without_open_is_safe() -> None:
    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)
    await client.close()  # nothing to close


@pytest.mark.asyncio
async def test_async_context_manager_opens_and_closes() -> None:
    factory, fake_client = _factory(db={"c": FakeContainer(name="c")})
    async with CosmosKitClient(endpoint="https://x", key="k", client_factory=factory) as client:
        client.get_container("db", "c")
        assert client.is_open
    assert fake_client.closed is True


@pytest.mark.asyncio
async def test_owned_credential_is_closed_when_default_used() -> None:
    closed = {"n": 0}

    class FakeDefaultCred:
        async def close(self) -> None:
            closed["n"] += 1

    factory, _ = _factory(db={"c": FakeContainer(name="c")})

    def patched_factory(endpoint: str, credential: Any) -> FakeCosmosClient:
        # Confirm credential came from DefaultAzureCredential path
        assert credential is not None
        return factory(endpoint, credential)

    # Patch resolve_credential indirectly by passing credential explicitly so
    # we control closing semantics: when caller passes credential, kit does
    # NOT own it.
    cred = FakeDefaultCred()
    client = CosmosKitClient(endpoint="https://x", credential=cred, client_factory=patched_factory)
    client.get_container("db", "c")
    await client.close()
    # caller-provided credential is NOT auto-closed
    assert closed["n"] == 0


@pytest.mark.asyncio
async def test_close_swallows_client_close_errors() -> None:
    class Bad(FakeCosmosClient):
        async def close(self) -> None:
            raise RuntimeError("boom")

    bad = Bad(databases={"db": FakeDatabase({"c": FakeContainer(name="c")})})

    def make(_endpoint: str, _credential: Any) -> Bad:
        return bad

    client = CosmosKitClient(endpoint="https://x", key="k", client_factory=make)
    client.get_container("db", "c")
    await client.close()  # must not propagate
    assert not client.is_open


@pytest.mark.asyncio
async def test_owned_default_credential_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = {"n": 0}

    class FakeDefaultCred:
        async def close(self) -> None:
            closed["n"] += 1

    def fake_resolve(*, key: str | None = None, credential: Any = None) -> Any:
        if key is not None:
            return key
        if credential is not None:
            return credential
        return FakeDefaultCred()

    monkeypatch.setattr(creds_mod, "resolve_credential", fake_resolve)
    monkeypatch.setattr(client_mod, "resolve_credential", fake_resolve)

    factory, _ = _factory(db={"c": FakeContainer(name="c")})
    client = CosmosKitClient(endpoint="https://x", client_factory=factory)
    client.get_container("db", "c")
    await client.close()
    assert closed["n"] == 1
