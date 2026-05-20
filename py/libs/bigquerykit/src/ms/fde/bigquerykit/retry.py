"""Rate-limit-aware async retry decorator.

The BigQuery SDK already retries internally for individual HTTP calls, but
higher-level loops (e.g. iterating result pages, polling a long-running job)
sometimes need an additional retry layer scoped to ``RateLimited`` errors.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from ms.fde.bigquerykit.errors import RateLimited

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def sleep_for_retry(
    retry_after_ms: int,
    *,
    attempt: int,
    base_ms: int = 250,
    cap_ms: int = 30_000,
) -> None:
    """Sleep for the suggested duration, falling back to capped exponential backoff."""
    if retry_after_ms > 0:
        delay = min(retry_after_ms, cap_ms)
    else:
        delay = min(base_ms * 2 ** max(attempt - 1, 0), cap_ms)
    await asyncio.sleep(delay / 1000.0)


def retry_on_rate_limit(
    *,
    max_attempts: int = 5,
    base_ms: int = 250,
    cap_ms: int = 30_000,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorate an async callable so ``RateLimited`` errors trigger bounded retries.

    Non-``RateLimited`` exceptions propagate immediately. After ``max_attempts``
    failed attempts, the final ``RateLimited`` is re-raised.
    """
    if max_attempts < 1:
        msg = "max_attempts must be >= 1"
        raise ValueError(msg)

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exc: RateLimited | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except RateLimited as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    logger.warning(
                        "BigQuery rate-limited (attempt %d/%d), retry_after_ms=%d",
                        attempt,
                        max_attempts,
                        exc.retry_after_ms,
                    )
                    await sleep_for_retry(
                        exc.retry_after_ms,
                        attempt=attempt,
                        base_ms=base_ms,
                        cap_ms=cap_ms,
                    )
            assert last_exc is not None  # loop guarantees this
            raise last_exc

        return wrapper

    return decorator
