"""Fake LLM client with FIFO response seeding and request tracking."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMRequest:
    """Captured request for assertion in tests."""

    messages: list[dict[str, str]]
    model: str | None = None
    temperature: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A single chunk in a streaming response."""

    text: str
    finish_reason: str | None = None


class FakeLLMClient:
    """FIFO-seeded fake LLM client for deterministic tests.

    Supports both synchronous ``complete()`` and async ``stream()``
    methods. Tracks all requests for assertion.

    Usage::

        llm = FakeLLMClient()
        llm.seed_complete("Hello!")
        llm.seed_complete("World!")

        result = await llm.complete(messages=[...])
        assert result == "Hello!"
        assert len(llm.requests) == 1
    """

    def __init__(self, *, fallback: str = "fake response") -> None:
        self._queue: deque[str | list[StreamChunk]] = deque()
        self._fallback = fallback
        self.requests: list[LLMRequest] = []

    def seed_complete(self, content: str) -> "FakeLLMClient":
        """Queue a synchronous response. Returns self for chaining."""
        self._queue.append(content)
        return self

    def seed_stream(self, chunks: list[str]) -> "FakeLLMClient":
        """Queue a streaming response as a list of text chunks."""
        self._queue.append([StreamChunk(text=t) for t in chunks])
        return self

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Return the next seeded response, or the fallback."""
        self.requests.append(
            LLMRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                extra=kwargs,
            )
        )
        if self._queue:
            response = self._queue.popleft()
            if isinstance(response, list):
                return "".join(c.text for c in response)
            return response
        return self._fallback

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ):
        """Yield chunks from the next seeded stream response."""
        self.requests.append(
            LLMRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                extra=kwargs,
            )
        )
        if self._queue:
            response = self._queue.popleft()
            if isinstance(response, list):
                for chunk in response:
                    yield chunk
                return
            yield StreamChunk(text=response, finish_reason="stop")
            return
        yield StreamChunk(text=self._fallback, finish_reason="stop")

    @property
    def last_request(self) -> LLMRequest | None:
        """The most recent request, or None."""
        return self.requests[-1] if self.requests else None

    def reset(self) -> None:
        """Clear all seeded responses and recorded requests."""
        self._queue.clear()
        self.requests.clear()
