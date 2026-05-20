import pytest

from ms.fde.bigquerykit.client import BigQueryKitClient
from ms.fde.bigquerykit.errors import BadRequest, RateLimited
from tests.fakes import FakeBigQueryClient


def _factory(fake: FakeBigQueryClient) -> object:
    return lambda project, creds, location: fake


@pytest.mark.asyncio
async def test_query_rows_yields_pages_and_converts_rows() -> None:
    fake = FakeBigQueryClient(
        pages_by_sql_substring={
            "FROM `p.d.learners`": [
                [{"id": "L-1", "country": "US"}, {"id": "L-2", "country": "DE"}],
                [{"id": "L-3", "country": "BR"}],
            ]
        }
    )
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        pages: list[list[dict]] = []
        async for page in ds.query_rows(f"SELECT * FROM `{ds.table_ref('learners')}`"):
            pages.append(page)
    assert [len(p) for p in pages] == [2, 1]
    assert pages[0][0]["id"] == "L-1"


@pytest.mark.asyncio
async def test_query_one_returns_first_row_only() -> None:
    fake = FakeBigQueryClient(
        pages_by_sql_substring={
            "FROM `p.d.t`": [[{"a": 1}, {"a": 2}]],
        }
    )
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        row = await ds.query_one(f"SELECT * FROM `{ds.table_ref('t')}`")
    assert row == {"a": 1}


@pytest.mark.asyncio
async def test_query_all_respects_max_rows() -> None:
    fake = FakeBigQueryClient(
        pages_by_sql_substring={
            "FROM `p.d.t`": [[{"a": 1}, {"a": 2}], [{"a": 3}]],
        }
    )
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        rows = await ds.query_all(f"SELECT * FROM `{ds.table_ref('t')}`", max_rows=2)
    assert rows == [{"a": 1}, {"a": 2}]


@pytest.mark.asyncio
async def test_count_parses_n_column() -> None:
    fake = FakeBigQueryClient(pages_by_sql_substring={"COUNT(*) AS n": [[{"n": 42}]]})
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        assert await ds.count("t") == 42


@pytest.mark.asyncio
async def test_query_rows_maps_429_to_rate_limited() -> None:
    class _Exc(Exception):
        code = 429

    fake = FakeBigQueryClient(raise_on_query=_Exc("slow"))
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        with pytest.raises(RateLimited):
            async for _ in ds.query_rows("SELECT 1"):
                pass


@pytest.mark.asyncio
async def test_insert_rows_raises_when_sdk_returns_errors() -> None:
    class _NoisyClient(FakeBigQueryClient):
        def insert_rows_json(self, ref: str, rows: list[dict]) -> list[dict]:
            return [{"index": 0, "errors": [{"reason": "invalid"}]}]

    fake = _NoisyClient()
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        with pytest.raises(BadRequest, match="rejected"):
            await ds.insert_rows("t", [{"id": "1"}])


@pytest.mark.asyncio
async def test_exists_table_true_and_false() -> None:
    fake = FakeBigQueryClient(existing_tables={"p.d.exists"})
    async with BigQueryKitClient(project="p", client_factory=_factory(fake)) as bq:
        ds = bq.get_dataset("d")
        assert await ds.exists_table("exists") is True
        assert await ds.exists_table("missing") is False


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    fake = FakeBigQueryClient()
    bq = BigQueryKitClient(project="p", client_factory=_factory(fake))
    await bq.__aenter__()
    await bq.close()
    assert fake.closed is True
    await bq.close()  # second close is a no-op
