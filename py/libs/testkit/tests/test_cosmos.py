"""Tests for FakeCosmosContainer."""

import pytest

from testkit import FakeCosmosContainer, assert_cosmos_item


class TestFakeCosmosContainer:
    async def test_create_and_read(self, cosmos):
        item = await cosmos.create_item({"id": "1", "session_id": "s1", "data": "hello"})
        assert item["_etag"]
        result = await cosmos.read_item("1", partition_key="s1")
        assert result["data"] == "hello"

    async def test_create_duplicate_raises(self, cosmos):
        await cosmos.create_item({"id": "1", "session_id": "s1"})
        with pytest.raises(ValueError, match="already exists"):
            await cosmos.create_item({"id": "1", "session_id": "s1"})

    async def test_upsert(self, cosmos):
        await cosmos.upsert_item({"id": "1", "session_id": "s1", "v": 1})
        await cosmos.upsert_item({"id": "1", "session_id": "s1", "v": 2})
        result = await cosmos.read_item("1", partition_key="s1")
        assert result["v"] == 2

    async def test_replace_with_etag(self, cosmos):
        created = await cosmos.create_item({"id": "1", "session_id": "s1", "v": 1})
        etag = created["_etag"]
        await cosmos.replace_item("1", {"id": "1", "session_id": "s1", "v": 2}, headers={"If-Match": etag})
        result = await cosmos.read_item("1", partition_key="s1")
        assert result["v"] == 2

    async def test_replace_stale_etag_raises(self, cosmos):
        await cosmos.create_item({"id": "1", "session_id": "s1", "v": 1})
        with pytest.raises(ValueError, match="ETag mismatch"):
            await cosmos.replace_item("1", {"id": "1", "session_id": "s1", "v": 2}, headers={"If-Match": '"stale"'})

    async def test_delete(self, cosmos):
        await cosmos.create_item({"id": "1", "session_id": "s1"})
        await cosmos.delete_item("1", partition_key="s1")
        with pytest.raises(KeyError):
            await cosmos.read_item("1", partition_key="s1")

    async def test_query_with_parameters(self, cosmos):
        await cosmos.create_item({"id": "1", "session_id": "s1", "role": "user"})
        await cosmos.create_item({"id": "2", "session_id": "s2", "role": "admin"})
        results = []
        async for item in cosmos.query_items(
            "SELECT * FROM c WHERE c.session_id = @session_id",
            parameters=[{"name": "@session_id", "value": "s1"}],
        ):
            results.append(item)
        assert len(results) == 1
        assert results[0]["id"] == "1"

    async def test_query_no_params_returns_all(self, cosmos):
        await cosmos.create_item({"id": "1", "session_id": "s1"})
        await cosmos.create_item({"id": "2", "session_id": "s2"})
        results = [item async for item in cosmos.query_items("SELECT * FROM c")]
        assert len(results) == 2

    def test_seed(self, cosmos):
        cosmos.seed({"id": "a", "session_id": "s1"}, {"id": "b", "session_id": "s2"})
        assert len(cosmos) == 2

    def test_all_items(self, cosmos):
        cosmos.seed({"id": "a", "session_id": "s1"})
        assert len(cosmos.all_items) == 1

    async def test_assert_cosmos_item(self, cosmos):
        await cosmos.create_item({"id": "x", "session_id": "s1", "status": "active"})
        item = assert_cosmos_item(cosmos, "x", field_checks={"status": "active"})
        assert item["id"] == "x"

    async def test_assert_cosmos_item_missing(self, cosmos):
        with pytest.raises(AssertionError, match="not found"):
            assert_cosmos_item(cosmos, "missing")
