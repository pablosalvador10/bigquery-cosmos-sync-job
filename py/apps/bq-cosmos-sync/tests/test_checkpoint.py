from datetime import UTC, datetime

import pytest

from bq_cosmos_sync.checkpoint import CheckpointStore
from bq_cosmos_sync.models import PipelineSummary
from tests.fakes import FakeCosmosContainer


@pytest.mark.asyncio
async def test_round_trip_summary_and_watermark() -> None:
    container = FakeCosmosContainer(name="sync_metadata")
    store = CheckpointStore(container)  # type: ignore[arg-type]

    wm_before = await store.read_watermark("learners")
    assert wm_before is None

    summary = PipelineSummary(
        pipeline_name="learners",
        status="success",
        rows_read=10,
        rows_upserted=10,
        rows_failed=0,
        duration_seconds=1.23,
        finished_at=datetime(2026, 5, 19, 2, 5, tzinfo=UTC),
    )
    new_wm = datetime(2026, 5, 19, 2, 0, tzinfo=UTC)
    await store.write_summary(summary, run_id="run-1", new_watermark=new_wm)

    again = await store.read_watermark("learners")
    assert again == new_wm

    stored = container.items[("learners", "learners")]
    assert stored["last_run_id"] == "run-1"
    assert stored["last_rows_upserted"] == 10
    assert stored["last_status"] == "success"
