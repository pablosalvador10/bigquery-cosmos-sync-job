"""Tests for ``CosmosContainer`` against the in-memory fake."""

import pytest

from ms.fde.cosmosdbkit.container import CosmosContainer
from ms.fde.cosmosdbkit.errors import Conflict, CosmosKitError, NotFound, Throttled
from tests.fakes import FakeContainer, FakeCosmosError


@pytest.fixture
def fake() -> FakeContainer:
    return FakeContainer(name="test", partition_field="hackathonId")


@pytest.fixture
def container(fake: FakeContainer) -> CosmosContainer:
    return CosmosContainer(fake, name="test")


def _doc(item_id: str, hackathon_id: str = "h1", **extra: object) -> dict[str, object]:
    return {"id": item_id, "hackathonId": hackathon_id, **extra}


# ---------------------------------------------------------------- construction


def test_name_is_returned(container: CosmosContainer) -> None:
    assert container.name == "test"


def test_name_falls_back_to_container_id() -> None:
    fake = FakeContainer(name="auto")
    c = CosmosContainer(fake)
    assert c.name == "auto"


# -------------------------------------------------------------------- upsert


@pytest.mark.asyncio
async def test_upsert_inserts(container: CosmosContainer, fake: FakeContainer) -> None:
    await container.upsert_item(_doc("a"))
    assert ("h1", "a") in fake._items


@pytest.mark.asyncio
async def test_upsert_replaces_existing(container: CosmosContainer, fake: FakeContainer) -> None:
    await container.upsert_item(_doc("a", v=1))
    await container.upsert_item(_doc("a", v=2))
    assert fake._items[("h1", "a")]["v"] == 2


@pytest.mark.asyncio
async def test_upsert_returns_body(container: CosmosContainer) -> None:
    out = await container.upsert_item(_doc("a", v=1))
    assert out["id"] == "a"


@pytest.mark.asyncio
async def test_upsert_translates_errors(container: CosmosContainer, fake: FakeContainer) -> None:
    async def boom(**_: object) -> dict[str, object]:
        raise FakeCosmosError(status_code=429, retry_after_ms=10)

    fake.upsert_item = boom  # type: ignore[method-assign]

    with pytest.raises(Throttled):
        await container.upsert_item(_doc("a"))


# --------------------------------------------------------------- create_item


@pytest.mark.asyncio
async def test_create_item_inserts(container: CosmosContainer, fake: FakeContainer) -> None:
    await container.create_item(_doc("a"))
    assert ("h1", "a") in fake._items


@pytest.mark.asyncio
async def test_create_item_raises_conflict_on_duplicate(container: CosmosContainer) -> None:
    await container.create_item(_doc("a"))
    with pytest.raises(Conflict):
        await container.create_item(_doc("a"))


# -------------------------------------------------------------- replace_item


@pytest.mark.asyncio
async def test_replace_item_updates(container: CosmosContainer, fake: FakeContainer) -> None:
    await container.create_item(_doc("a", v=1))
    await container.replace_item("a", _doc("a", v=2))
    assert fake._items[("h1", "a")]["v"] == 2


@pytest.mark.asyncio
async def test_replace_item_raises_not_found(container: CosmosContainer) -> None:
    with pytest.raises(NotFound):
        await container.replace_item("missing", _doc("missing"))


# -------------------------------------------------------------- delete_item


@pytest.mark.asyncio
async def test_delete_item_removes(container: CosmosContainer, fake: FakeContainer) -> None:
    await container.create_item(_doc("a"))
    await container.delete_item("a", "h1")
    assert ("h1", "a") not in fake._items


@pytest.mark.asyncio
async def test_delete_item_swallows_not_found(container: CosmosContainer) -> None:
    # Should NOT raise.
    await container.delete_item("missing", "h1")


@pytest.mark.asyncio
async def test_delete_item_propagates_other_errors(container: CosmosContainer, fake: FakeContainer) -> None:
    async def boom(**_: object) -> None:
        raise FakeCosmosError(status_code=500)

    fake.delete_item = boom  # type: ignore[method-assign]
    with pytest.raises(CosmosKitError):
        await container.delete_item("a", "h1")


# ----------------------------------------------------------------- read_item


@pytest.mark.asyncio
async def test_read_item_returns_doc(container: CosmosContainer) -> None:
    await container.create_item(_doc("a", v=1))
    out = await container.read_item("a", "h1")
    assert out["v"] == 1


@pytest.mark.asyncio
async def test_read_item_raises_not_found(container: CosmosContainer) -> None:
    with pytest.raises(NotFound):
        await container.read_item("missing", "h1")


@pytest.mark.asyncio
async def test_try_read_item_returns_none_when_missing(container: CosmosContainer) -> None:
    assert await container.try_read_item("missing", "h1") is None


@pytest.mark.asyncio
async def test_try_read_item_returns_doc_when_present(container: CosmosContainer) -> None:
    await container.create_item(_doc("a", v=1))
    out = await container.try_read_item("a", "h1")
    assert out is not None
    assert out["v"] == 1


# ----------------------------------------------------------------- query_items


@pytest.mark.asyncio
async def test_query_items_with_partition_key(container: CosmosContainer) -> None:
    await container.create_item(_doc("a"))
    await container.create_item(_doc("b"))
    items = []
    async for item in container.query_items(
        "SELECT * FROM c WHERE c.hackathonId = @hid",
        {"hid": "h1"},
        partition_key="h1",
    ):
        items.append(item)
    assert len(items) == 2


@pytest.mark.asyncio
async def test_query_items_normalizes_dict_parameters(
    container: CosmosContainer, fake: FakeContainer
) -> None:
    await container.create_item(_doc("a"))
    aiter_ = container.query_items("SELECT * FROM c WHERE c.id = @id", {"id": "a"})
    async for _ in aiter_:
        pass
    last = fake.calls[-1]
    assert last[1]["parameters"] == [{"name": "@id", "value": "a"}]


@pytest.mark.asyncio
async def test_query_items_accepts_list_parameters(container: CosmosContainer) -> None:
    await container.create_item(_doc("a"))
    items = [
        i
        async for i in container.query_items(
            "SELECT * FROM c WHERE c.id = @id",
            [{"name": "@id", "value": "a"}],
        )
    ]
    assert len(items) == 1


@pytest.mark.asyncio
async def test_query_items_no_match(container: CosmosContainer) -> None:
    items = [i async for i in container.query_items("SELECT * FROM c WHERE c.id = @id", {"id": "nope"})]
    assert items == []


# -------------------------------------------------------------- read_all_items


@pytest.mark.asyncio
async def test_read_all_items(container: CosmosContainer) -> None:
    await container.create_item(_doc("a"))
    await container.create_item(_doc("b", hackathon_id="h2"))
    items = [i async for i in container.read_all_items()]
    assert len(items) == 2


@pytest.mark.asyncio
async def test_read_all_items_with_partition_filter(container: CosmosContainer) -> None:
    await container.create_item(_doc("a"))
    await container.create_item(_doc("b", hackathon_id="h2"))
    items = [i async for i in container.read_all_items(partition_key="h1")]
    assert {i["id"] for i in items} == {"a"}


# ------------------------------------------------------------------ query_one


@pytest.mark.asyncio
async def test_query_one_returns_first(container: CosmosContainer) -> None:
    await container.create_item(_doc("a", v=1))
    await container.create_item(_doc("b", v=2))
    out = await container.query_one("SELECT * FROM c WHERE c.hackathonId = @hid", {"hid": "h1"})
    assert out is not None


@pytest.mark.asyncio
async def test_query_one_returns_none_when_no_match(container: CosmosContainer) -> None:
    out = await container.query_one("SELECT * FROM c WHERE c.id = @id", {"id": "nope"})
    assert out is None


# ------------------------------------------------------------------ query_all


@pytest.mark.asyncio
async def test_query_all_materializes(container: CosmosContainer) -> None:
    for i in range(5):
        await container.create_item(_doc(f"x{i}"))
    items = await container.query_all("SELECT * FROM c WHERE c.hackathonId = @hid", {"hid": "h1"})
    assert len(items) == 5


@pytest.mark.asyncio
async def test_query_all_respects_max_items(container: CosmosContainer) -> None:
    for i in range(5):
        await container.create_item(_doc(f"x{i}"))
    items = await container.query_all(
        "SELECT * FROM c WHERE c.hackathonId = @hid", {"hid": "h1"}, max_items=2
    )
    assert len(items) == 2


@pytest.mark.asyncio
async def test_query_all_rejects_zero_max_items(container: CosmosContainer) -> None:
    with pytest.raises(ValueError):
        await container.query_all("SELECT * FROM c", max_items=0)


@pytest.mark.asyncio
async def test_query_all_rejects_negative_max_items(container: CosmosContainer) -> None:
    with pytest.raises(ValueError):
        await container.query_all("SELECT * FROM c", max_items=-1)


@pytest.mark.asyncio
async def test_query_all_translates_errors(container: CosmosContainer, fake: FakeContainer) -> None:
    def bad_query(**_: object):  # type: ignore[no-untyped-def]
        async def gen():  # type: ignore[no-untyped-def]
            raise FakeCosmosError(status_code=429, retry_after_ms=1)
            yield  # pragma: no cover

        return gen()

    fake.query_items = bad_query  # type: ignore[assignment]

    with pytest.raises(Throttled):
        await container.query_all("SELECT * FROM c")


# --------------------------------------------------------------------- count


@pytest.mark.asyncio
async def test_count_with_scalar_value_rows(container: CosmosContainer) -> None:
    for i in range(3):
        await container.create_item(_doc(f"x{i}"))
    n = await container.count("SELECT VALUE COUNT(1) FROM c WHERE c.hackathonId = @hid", {"hid": "h1"})
    assert n == 3


@pytest.mark.asyncio
async def test_count_returns_zero_when_no_rows(container: CosmosContainer, fake: FakeContainer) -> None:
    # Force an empty iterator
    async def empty(**_: object):  # type: ignore[no-untyped-def]
        if False:
            yield  # pragma: no cover

    fake.query_items = empty  # type: ignore[assignment]
    n = await container.count("SELECT VALUE COUNT(1) FROM c")
    assert n == 0


@pytest.mark.asyncio
async def test_count_rejects_non_scalar_rows(container: CosmosContainer, fake: FakeContainer) -> None:
    async def gen(**_: object):  # type: ignore[no-untyped-def]
        yield {"a": 1, "b": 2}

    fake.query_items = gen  # type: ignore[assignment]
    with pytest.raises(CosmosKitError):
        await container.count("SELECT * FROM c")


@pytest.mark.asyncio
async def test_count_handles_dict_with_single_numeric_value(
    container: CosmosContainer, fake: FakeContainer
) -> None:
    async def gen(**_: object):  # type: ignore[no-untyped-def]
        yield {"$1": 5}

    fake.query_items = gen  # type: ignore[assignment]
    n = await container.count("SELECT * FROM c")
    assert n == 5


# ---------------------------------------------------------- protocol shape


def test_container_exposes_protocol_methods(container: CosmosContainer) -> None:
    # Sanity: ContainerProxy expects these names.
    for name in ("upsert_item", "create_item", "read_item", "query_items", "read_all_items"):
        assert hasattr(container, name)
