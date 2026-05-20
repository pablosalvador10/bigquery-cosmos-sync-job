import asyncio

import pytest

from ms.fde.bigquerykit.errors import RateLimited
from ms.fde.bigquerykit.retry import retry_on_rate_limit, sleep_for_retry


@pytest.mark.asyncio
async def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    calls = {"n": 0}

    @retry_on_rate_limit(max_attempts=4, base_ms=1, cap_ms=1)
    async def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimited("slow down", retry_after_ms=1)
        return "ok"

    assert await fn() == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_gives_up_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    @retry_on_rate_limit(max_attempts=2, base_ms=1, cap_ms=1)
    async def fn() -> None:
        raise RateLimited("nope", retry_after_ms=0)

    with pytest.raises(RateLimited):
        await fn()


@pytest.mark.asyncio
async def test_non_rate_limit_errors_propagate_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    calls = {"n": 0}

    @retry_on_rate_limit(max_attempts=4, base_ms=1, cap_ms=1)
    async def fn() -> None:
        calls["n"] += 1
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError):
        await fn()
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_sleep_for_retry_uses_hint_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[float] = []

    async def _fake(delay: float) -> None:
        seen.append(delay)

    monkeypatch.setattr(asyncio, "sleep", _fake)
    await sleep_for_retry(2_000, attempt=1, base_ms=1, cap_ms=10_000)
    assert seen == [2.0]


def test_max_attempts_zero_rejected() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        retry_on_rate_limit(max_attempts=0)
