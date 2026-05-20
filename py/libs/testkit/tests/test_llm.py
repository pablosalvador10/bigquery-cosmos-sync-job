"""Tests for FakeLLMClient."""

import pytest

from testkit import FakeLLMClient


class TestFakeLLMClient:
    async def test_complete_returns_seeded(self, llm):
        llm.seed_complete("hello")
        result = await llm.complete(messages=[{"role": "user", "content": "hi"}])
        assert result == "hello"

    async def test_complete_returns_fallback(self, llm):
        result = await llm.complete(messages=[{"role": "user", "content": "hi"}])
        assert result == "fake response"

    async def test_fifo_order(self, llm):
        llm.seed_complete("first").seed_complete("second")
        r1 = await llm.complete(messages=[])
        r2 = await llm.complete(messages=[])
        assert r1 == "first"
        assert r2 == "second"

    async def test_tracks_requests(self, llm):
        llm.seed_complete("ok")
        await llm.complete(messages=[{"role": "user", "content": "test"}], model="gpt-4")
        assert len(llm.requests) == 1
        assert llm.last_request.model == "gpt-4"
        assert llm.last_request.messages[0]["content"] == "test"

    async def test_stream_yields_chunks(self, llm):
        llm.seed_stream(["hello ", "world"])
        chunks = []
        async for chunk in llm.stream(messages=[]):
            chunks.append(chunk.text)
        assert chunks == ["hello ", "world"]

    async def test_stream_fallback(self, llm):
        chunks = []
        async for chunk in llm.stream(messages=[]):
            chunks.append(chunk.text)
        assert chunks == ["fake response"]

    async def test_reset(self, llm):
        llm.seed_complete("test")
        await llm.complete(messages=[])
        llm.reset()
        assert len(llm.requests) == 0
        result = await llm.complete(messages=[])
        assert result == "fake response"
