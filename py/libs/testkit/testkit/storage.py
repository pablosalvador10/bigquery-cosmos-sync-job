"""Fake storage implementing the template's Storage protocol."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class StoredMessage(BaseModel):
    """Message stored in the fake storage backend."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class FakeStorage:
    """In-memory storage implementing the template's Storage protocol.

    Usage::

        storage = FakeStorage()
        msg = StoredMessage(session_id="s1", role="user", content="hi")
        await storage.add_message(msg)
        msgs = await storage.list_messages("s1")
        assert len(msgs) == 1
    """

    def __init__(self) -> None:
        self._messages: dict[str, list[StoredMessage]] = defaultdict(list)

    async def add_message(self, message: StoredMessage) -> StoredMessage:
        self._messages[message.session_id].append(message)
        return message

    async def list_messages(self, session_id: str) -> list[StoredMessage]:
        return self._messages.get(session_id, [])

    # ── Test helpers ─────────────────────────────────────────────── #

    def assert_message_stored(self, session_id: str, role: str, content_contains: str) -> None:
        """Assert a message with the given role and content substring exists."""
        messages = self._messages.get(session_id, [])
        matches = [m for m in messages if m.role == role and content_contains in m.content]
        assert matches, (
            f"No {role} message containing '{content_contains}' "
            f"in session {session_id}. Found: {[m.content[:50] for m in messages]}"
        )

    def assert_session_has_messages(self, session_id: str, count: int) -> None:
        """Assert the session has exactly ``count`` messages."""
        actual = len(self._messages.get(session_id, []))
        assert actual == count, f"Expected {count} messages in {session_id}, got {actual}"

    @property
    def all_messages(self) -> list[StoredMessage]:
        """All messages across all sessions."""
        return [m for msgs in self._messages.values() for m in msgs]

    def reset(self) -> None:
        """Clear all stored messages."""
        self._messages.clear()
