"""Tests for FakeStorage."""

import pytest

from testkit import FakeStorage
from testkit.storage import StoredMessage


class TestFakeStorage:
    async def test_add_and_list(self, storage):
        msg = StoredMessage(session_id="s1", role="user", content="hello")
        await storage.add_message(msg)
        messages = await storage.list_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "hello"

    async def test_empty_session(self, storage):
        messages = await storage.list_messages("nonexistent")
        assert messages == []

    async def test_multiple_sessions(self, storage):
        await storage.add_message(StoredMessage(session_id="s1", role="user", content="a"))
        await storage.add_message(StoredMessage(session_id="s2", role="user", content="b"))
        assert len(await storage.list_messages("s1")) == 1
        assert len(await storage.list_messages("s2")) == 1

    async def test_assert_message_stored(self, storage):
        await storage.add_message(StoredMessage(session_id="s1", role="user", content="hello world"))
        storage.assert_message_stored("s1", "user", "hello")

    async def test_assert_message_stored_fails(self, storage):
        with pytest.raises(AssertionError):
            storage.assert_message_stored("s1", "user", "missing")

    async def test_assert_session_has_messages(self, storage):
        await storage.add_message(StoredMessage(session_id="s1", role="user", content="a"))
        await storage.add_message(StoredMessage(session_id="s1", role="assistant", content="b"))
        storage.assert_session_has_messages("s1", 2)

    async def test_all_messages(self, storage):
        await storage.add_message(StoredMessage(session_id="s1", role="user", content="a"))
        await storage.add_message(StoredMessage(session_id="s2", role="user", content="b"))
        assert len(storage.all_messages) == 2

    async def test_reset(self, storage):
        await storage.add_message(StoredMessage(session_id="s1", role="user", content="a"))
        storage.reset()
        assert len(storage.all_messages) == 0
