"""Bounded-concurrency upserter: semaphore + 429 retry + per-row isolation."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from ms.fde.cosmosdbkit.container import CosmosContainer
from ms.fde.cosmosdbkit.errors import CosmosKitError
from ms.fde.cosmosdbkit.retry import retry_on_throttle

logger = logging.getLogger(__name__)


@dataclass
class BatchWriteResult:
    upserted: int = 0
    failed: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)

    def merge(self, other: "BatchWriteResult") -> None:
        self.upserted += other.upserted
        self.failed += other.failed
        self.failures.extend(other.failures)


class BatchWriter:
    def __init__(
        self,
        container: CosmosContainer,
        *,
        concurrency: int = 16,
        max_failure_samples: int = 25,
    ) -> None:
        if concurrency < 1:
            msg = "concurrency must be >= 1"
            raise ValueError(msg)
        self._container = container
        self._sem = asyncio.Semaphore(concurrency)
        self._max_failure_samples = max_failure_samples

    async def upsert_batch(self, documents: list[dict[str, Any]]) -> BatchWriteResult:
        if not documents:
            return BatchWriteResult()
        result = BatchWriteResult()
        outcomes = await asyncio.gather(
            *(self._upsert_one(d) for d in documents),
            return_exceptions=False,
        )
        for ok, doc_id, error in outcomes:
            if ok:
                result.upserted += 1
            else:
                result.failed += 1
                if len(result.failures) < self._max_failure_samples:
                    result.failures.append({"id": doc_id, "error": error})
        return result

    @retry_on_throttle(max_attempts=5)
    async def _do_upsert(self, body: dict[str, Any]) -> None:
        await self._container.upsert_item(body)

    async def _upsert_one(self, body: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        doc_id = str(body.get("id", "<missing-id>"))
        async with self._sem:
            try:
                await self._do_upsert(body)
                return True, doc_id, None
            except CosmosKitError as exc:
                logger.warning("Cosmos upsert failed id=%s: %s", doc_id, exc)
                return False, doc_id, f"{type(exc).__name__}: {exc}"
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unexpected upsert error id=%s", doc_id, exc_info=True)
                return False, doc_id, f"{type(exc).__name__}: {exc}"
