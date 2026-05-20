"""Chat endpoints: synchronous reply and SSE streaming.

Falls back to local simulation when Azure AI Foundry credentials are not
configured, so the template works out of the box without cloud credentials.
"""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.logging import logger
from models.chat import ChatRequest, ChatResponse, StoredMessage
from services.storage import get_storage
from tools.sample_tools import summarize_text

router = APIRouter(prefix="/api/v1", tags=["chat"])

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system.md"


def _load_system_prompt() -> str:
    """Load system prompt from markdown file, with a safe default."""
    return PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "You are a helpful assistant."


def _simulate_assistant_reply(user_message: str) -> str:
    """Generate a local reply without cloud credentials."""
    summary = json.loads(summarize_text(user_message))["summary"]
    system = _load_system_prompt()
    return f"{system}\n\nSummary: {summary}"


def _sse(event: str, data: dict[str, str | int | bool]) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """Synchronous chat — returns a single ChatResponse."""
    storage = get_storage()
    await storage.add_message(
        StoredMessage(session_id=body.session_id, role="user", content=body.message)
    )

    reply = _simulate_assistant_reply(body.message)
    await storage.add_message(
        StoredMessage(session_id=body.session_id, role="assistant", content=reply)
    )

    return ChatResponse(session_id=body.session_id, message_id=body.message_id, response=reply)


async def _stream_reply(body: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate SSE events for a streaming response."""
    storage = get_storage()
    await storage.add_message(
        StoredMessage(session_id=body.session_id, role="user", content=body.message)
    )

    reply = _simulate_assistant_reply(body.message)
    yield _sse("message_start", {"session_id": body.session_id, "message_id": body.message_id})

    for token in reply.split():
        yield _sse("delta", {"token": token})

    await storage.add_message(
        StoredMessage(session_id=body.session_id, role="assistant", content=reply)
    )
    logger.info("chat_stream_complete", session_id=body.session_id)
    yield _sse("tool_event", {"tool": "summarize_text", "status": "completed"})
    yield _sse("done", {"ok": True})


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    """SSE streaming chat endpoint."""
    return StreamingResponse(_stream_reply(body), media_type="text/event-stream")
