"""429-aware async retry decorator.

Cosmos throttles with ``HTTP 429`` plus a ``retry_after_ms`` hint. The Azure SDK
already retries internally for the request itself, but in higher-level code we
sometimes need an extra retry layer (for example, around batched query loops).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from ms.fde.cosmosdbkit.errors import Throttled

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def sleep_for_retry(
    retry_after_ms: int, *, attempt: int, base_ms: int = 100, cap_ms: int = 5_000
) -> None:
    """Sleep for the SDK-suggested duration, falling back to capped exponential backoff."""
    delay = (
        min(retry_after_ms, cap_ms) if retry_after_ms > 0 else min(base_ms * 2 ** max(attempt - 1, 0), cap_ms)
    )
    await asyncio.sleep(delay / 1000.0)


def retry_on_throttle(
    *,
    max_attempts: int = 5,
    base_ms: int = 100,
    cap_ms: int = 5_000,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorate an async callable so ``Throttled`` errors trigger bounded retries.

    Non-``Throttled`` exceptions propagate immediately. After ``max_attempts``
    failed attempts, the final ``Throttled`` is re-raised.
    """
    if max_attempts < 1:
        msg = "max_attempts must be >= 1"
        raise ValueError(msg)

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exc: Throttled | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Throttled as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    logger.warning(
                        "Cosmos throttled (attempt %d/%d), retry_after_ms=%d",
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
