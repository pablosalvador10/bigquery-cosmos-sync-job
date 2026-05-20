"""Tests for the 429 retry decorator."""

import pytest

from ms.fde.cosmosdbkit.errors import NotFound, Throttled
from ms.fde.cosmosdbkit.retry import retry_on_throttle, sleep_for_retry


@pytest.mark.asyncio
async def test_returns_value_when_no_throttle() -> None:
    @retry_on_throttle(max_attempts=3)
    async def op() -> int:
        return 42

    assert await op() == 42


@pytest.mark.asyncio
async def test_retries_until_success() -> None:
    calls = {"n": 0}

    @retry_on_throttle(max_attempts=4, base_ms=1, cap_ms=2)
    async def op() -> int:
        calls["n"] += 1
        if calls["n"] < 3:
            raise Throttled("x", retry_after_ms=1)
        return 7

    assert await op() == 7
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_reraises_after_max_attempts() -> None:
    @retry_on_throttle(max_attempts=2, base_ms=1, cap_ms=1)
    async def op() -> int:
        raise Throttled("x", retry_after_ms=1)

    with pytest.raises(Throttled):
        await op()


@pytest.mark.asyncio
async def test_non_throttled_propagates_immediately() -> None:
    calls = {"n": 0}

    @retry_on_throttle(max_attempts=3, base_ms=1, cap_ms=1)
    async def op() -> int:
        calls["n"] += 1
        raise NotFound("nope")

    with pytest.raises(NotFound):
        await op()
    assert calls["n"] == 1


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError):
        retry_on_throttle(max_attempts=0)


@pytest.mark.asyncio
async def test_decorator_preserves_function_metadata() -> None:
    @retry_on_throttle()
    async def my_op() -> str:
        """docstring"""
        return "ok"

    assert my_op.__name__ == "my_op"
    assert my_op.__doc__ == "docstring"


@pytest.mark.asyncio
async def test_sleep_for_retry_uses_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    await sleep_for_retry(150, attempt=1, base_ms=10, cap_ms=1000)
    assert slept == [0.15]


@pytest.mark.asyncio
async def test_sleep_for_retry_falls_back_to_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    await sleep_for_retry(0, attempt=3, base_ms=10, cap_ms=1000)
    # 10 * 2**(3-1) = 40ms = 0.04s
    assert slept == [0.04]


@pytest.mark.asyncio
async def test_sleep_for_retry_caps_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    await sleep_for_retry(999_999, attempt=1, base_ms=10, cap_ms=2_000)
    assert slept == [2.0]


@pytest.mark.asyncio
async def test_retry_passes_args_through() -> None:
    @retry_on_throttle(max_attempts=2, base_ms=1, cap_ms=1)
    async def op(a: int, b: int = 0) -> int:
        return a + b

    assert await op(2, b=3) == 5


@pytest.mark.asyncio
async def test_retry_uses_hint_from_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(s: float) -> None:
        slept.append(s)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
    calls = {"n": 0}

    @retry_on_throttle(max_attempts=2, base_ms=10, cap_ms=1000)
    async def op() -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise Throttled("x", retry_after_ms=42)
        return 1

    assert await op() == 1
    assert slept == [0.042]


@pytest.mark.asyncio
async def test_retry_attempt_one_means_one_call() -> None:
    calls = {"n": 0}

    @retry_on_throttle(max_attempts=1, base_ms=1, cap_ms=1)
    async def op() -> int:
        calls["n"] += 1
        raise Throttled("x")

    with pytest.raises(Throttled):
        await op()
    assert calls["n"] == 1
