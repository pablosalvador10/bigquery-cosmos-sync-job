"""Tests for synchronous chat and health endpoints."""

from fastapi.testclient import TestClient

from main import app


def test_healthz_returns_ok() -> None:
    """Health endpoint returns 200 with status ok."""
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_summary_response() -> None:
    """Chat endpoint returns a response containing a summary."""
    client = TestClient(app)
    payload = {"message": "Explain SSE in one line."}
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response"]
    assert "Summary:" in data["response"]
