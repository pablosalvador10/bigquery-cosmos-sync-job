import pytest

from bq_cosmos_sync.config import Settings


def _base_env(**overrides: str) -> dict[str, str]:
    env = {
        "BQ_PROJECT_ID": "test-proj",
        "COSMOS_ENDPOINT": "https://example.documents.azure.com:443/",
    }
    env.update(overrides)
    return env


def test_loads_with_minimum_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _base_env().items():
        monkeypatch.setenv(k, v)
    s = Settings()  # type: ignore[call-arg]
    s.validate_runtime()
    assert s.bq_project_id == "test-proj"
    assert s.cosmos_database == "learnsphere"
    assert s.sync_pipelines == []


def test_pipelines_csv_is_split(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _base_env(SYNC_PIPELINES="courses, learners ,recommendations").items():
        monkeypatch.setenv(k, v)
    s = Settings()  # type: ignore[call-arg]
    assert s.sync_pipelines == ["courses", "learners", "recommendations"]


def test_invalid_cosmos_endpoint_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _base_env(COSMOS_ENDPOINT="example.documents.azure.com").items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValueError, match="https"):
        Settings()  # type: ignore[call-arg]


def test_legacy_cosmos_key_env_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """COSMOS_KEY / COSMOS_AUTH_MODE are not supported fields; setting them must be a no-op."""
    for k, v in _base_env(COSMOS_AUTH_MODE="key", COSMOS_KEY="ignored").items():
        monkeypatch.setenv(k, v)
    s = Settings()  # type: ignore[call-arg]
    s.validate_runtime()
    assert not hasattr(s, "cosmos_key")
    assert not hasattr(s, "cosmos_auth_mode")


def test_emulator_key_accepted_for_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env(
        COSMOS_ENDPOINT="https://localhost:8081/",
        COSMOS_EMULATOR_KEY="abc",
    )
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = Settings()  # type: ignore[call-arg]
    s.validate_runtime()
    assert s.cosmos_emulator_key == "abc"


def test_emulator_key_rejected_for_azure_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _base_env(COSMOS_EMULATOR_KEY="abc")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = Settings()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="cosmos_emulator_key"):
        s.validate_runtime()
