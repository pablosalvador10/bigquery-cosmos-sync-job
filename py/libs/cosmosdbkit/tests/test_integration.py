"""End-to-end tests against the in-memory fake — exercises the full kit."""

from typing import Any

import pytest

from ms.fde.cosmosdbkit import CosmosKitClient, NotFound, QueryBuilder, Throttled, retry_on_throttle
from tests.fakes import FakeContainer, FakeCosmosClient, FakeDatabase, ThrottlingContainer


def _make_client(
    container: FakeContainer, *, db_name: str = "fde", c_name: str = "submissions"
) -> CosmosKitClient:
    fake_client = FakeCosmosClient(databases={db_name: FakeDatabase({c_name: container})})

    def factory(_e: str, _c: Any) -> FakeCosmosClient:
        return fake_client

    return CosmosKitClient(endpoint="https://x", key="k", client_factory=factory)


@pytest.mark.asyncio
async def test_full_round_trip_via_client() -> None:
    fake = FakeContainer(name="submissions", partition_field="hackathonId")
    kit = _make_client(fake)
    container = kit.get_container("fde", "submissions")
    await container.upsert_item({"id": "s1", "hackathonId": "fde-fy26", "score": 87})
    out = await container.read_item("s1", "fde-fy26")
    assert out["score"] == 87
    await kit.close()


@pytest.mark.asyncio
async def test_query_builder_used_with_container() -> None:
    fake = FakeContainer(name="submissions", partition_field="hackathonId")
    kit = _make_client(fake)
    container = kit.get_container("fde", "submissions")
    await container.upsert_item({"id": "s1", "hackathonId": "fde-fy26"})
    sql, params = QueryBuilder("SELECT * FROM c WHERE c.id = @id").bind("id", "s1").build()
    items = await container.query_all(sql, params)
    assert len(items) == 1
    await kit.close()


@pytest.mark.asyncio
async def test_retry_decorator_recovers_throttled_read() -> None:
    fake = ThrottlingContainer(throttle_count=2, retry_after_ms=1)
    fake._items[("h1", "a")] = {"id": "a", "hackathonId": "h1"}
    kit = _make_client(fake)
    container = kit.get_container("fde", "submissions")

    @retry_on_throttle(max_attempts=4, base_ms=1, cap_ms=2)
    async def fetch() -> dict[str, Any]:
        return await container.read_item("a", "h1")

    out = await fetch()
    assert out["id"] == "a"
    await kit.close()


@pytest.mark.asyncio
async def test_retry_decorator_eventually_gives_up() -> None:
    fake = ThrottlingContainer(throttle_count=99, retry_after_ms=1)
    kit = _make_client(fake)
    container = kit.get_container("fde", "submissions")

    @retry_on_throttle(max_attempts=2, base_ms=1, cap_ms=2)
    async def fetch() -> dict[str, Any]:
        return await container.read_item("a", "h1")

    with pytest.raises(Throttled):
        await fetch()
    await kit.close()


@pytest.mark.asyncio
async def test_try_read_item_handles_real_404() -> None:
    fake = FakeContainer(name="submissions", partition_field="hackathonId")
    kit = _make_client(fake)
    container = kit.get_container("fde", "submissions")
    assert await container.try_read_item("missing", "h1") is None
    with pytest.raises(NotFound):
        await container.read_item("missing", "h1")
    await kit.close()
