import pytest

from ms.fde.bigquerykit.credentials import resolve_credentials


def test_returns_none_when_no_inputs() -> None:
    creds, project = resolve_credentials()
    assert creds is None
    assert project is None


def test_rejects_multiple_sources() -> None:
    with pytest.raises(ValueError, match="at most one"):
        resolve_credentials(credentials_path="x.json", credentials_info={"a": 1})


def test_returns_explicit_credentials_object() -> None:
    class _Fake:
        project_id = "proj-123"

    cred = _Fake()
    out, project = resolve_credentials(credentials=cred)
    assert out is cred
    assert project == "proj-123"
