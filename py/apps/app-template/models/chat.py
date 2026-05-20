"""Pydantic models for chat API request/response and message persistence."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Synchronous chat response payload."""

    session_id: str
    message_id: str
    response: str


class StoredMessage(BaseModel):
    """Message persisted to storage with session partitioning."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
