"""Sample agent tool functions for the template app.

These functions work standalone for the simulation path.
When foundrykit is available, they can be registered via ToolRegistry
for use with Azure AI Foundry agents.
"""

import json

import httpx


def summarize_text(text: str) -> str:
    """Summarize input text. Returns JSON with a short summary and word count."""
    words = text.split()
    summary = " ".join(words[: min(len(words), 24)])
    return json.dumps({"summary": summary, "word_count": len(words)})


def fetch_data_api(url: str) -> str:
    """Fetch JSON from a URL and return a preview of the payload."""
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    payload = response.json()
    return json.dumps({"url": url, "keys": list(payload)[:10], "preview": payload})
