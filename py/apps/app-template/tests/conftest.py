"""Shared test fixtures for the template backend app."""

import pytest

from core.config import get_settings
from services import storage as storage_module


@pytest.fixture(autouse=True)
def force_inmemory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force in-memory storage and reset singletons between tests."""
    monkeypatch.setenv("STORAGE_MODE", "inmemory")
    get_settings.cache_clear()
    storage_module._storage = None
