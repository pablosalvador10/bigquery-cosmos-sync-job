import pytest

from bq_cosmos_sync.checkpoint import CheckpointStore
from bq_cosmos_sync.cosmos.writer import BatchWriter
from bq_cosmos_sync.pipelines.registry import default_registry
from bq_cosmos_sync.runner import SyncRunner
from tests.fakes import FakeBigQueryReader, FakeCosmosContainer


def _course_pages() -> list[list[dict[str, object]]]:
    return [
        [
            {
                "course_id": "C-1",
                "title": "T1",
                "category": "tech",
                "level": "beginner",
                "duration_minutes": 30,
                "price_usd": 9.99,
                "updated_at": None,
            },
            {
                "course_id": "C-2",
                "title": "T2",
                "category": "design",
                "level": "intermediate",
                "duration_minutes": 45,
                "price_usd": 19.99,
                "updated_at": None,
            },
        ],
        [
            {
                "course_id": "C-3",
                "title": "T3",
                "category": "tech",
                "level": "advanced",
                "duration_minutes": 60,
                "price_usd": 29.99,
                "updated_at": None,
            },
        ],
    ]


@pytest.mark.asyncio
async def test_run_writes_documents_and_summary() -> None:
    bq = FakeBigQueryReader({"FROM `p.d.courses`": _course_pages()})
    target = FakeCosmosContainer(name="courses")
    meta = FakeCosmosContainer(name="sync_metadata")
    store = CheckpointStore(meta)  # type: ignore[arg-type]

    def factory(name: str) -> BatchWriter:
        assert name == "courses"
        return BatchWriter(target, concurrency=4)  # type: ignore[arg-type]

    runner = SyncRunner(
        bq_dataset=bq,  # type: ignore[arg-type]
        get_writer=factory,
        checkpoint_store=store,
        pipelines=[default_registry().build("courses")],
        project_id="p",
        dataset="d",
        run_id="run-1",
        batch_size=10,
    )
    summary = await runner.run()

    assert summary.status == "success"
    assert summary.rows_read == 3
    assert summary.rows_upserted == 3
    assert summary.rows_failed == 0
    assert target.upsert_calls == 3
    # Checkpoint summary written
    assert ("courses", "courses") in meta.items


@pytest.mark.asyncio
async def test_dry_run_does_not_write_to_cosmos() -> None:
    bq = FakeBigQueryReader({"FROM `p.d.courses`": _course_pages()})
    target = FakeCosmosContainer(name="courses")
    meta = FakeCosmosContainer(name="sync_metadata")

    def factory(name: str) -> BatchWriter:
        return BatchWriter(target, concurrency=4)  # type: ignore[arg-type]

    runner = SyncRunner(
        bq_dataset=bq,  # type: ignore[arg-type]
        get_writer=factory,
        checkpoint_store=CheckpointStore(meta),  # type: ignore[arg-type]
        pipelines=[default_registry().build("courses")],
        project_id="p",
        dataset="d",
        run_id="run-dry",
        dry_run=True,
    )
    summary = await runner.run()
    assert summary.rows_read == 3
    assert summary.rows_upserted == 0
    assert target.upsert_calls == 0
    # No checkpoint written in dry-run
    assert meta.items == {}


@pytest.mark.asyncio
async def test_bad_row_is_isolated_and_counted_as_failure() -> None:
    pages = [
        [
            # Missing required course_id -> projection raises -> rows_failed += 1
            {
                "title": "Bad",
                "category": "tech",
                "level": "x",
                "duration_minutes": 10,
                "price_usd": 0,
                "updated_at": None,
            },
            {
                "course_id": "C-OK",
                "title": "Good",
                "category": "tech",
                "level": "x",
                "duration_minutes": 10,
                "price_usd": 0,
                "updated_at": None,
            },
        ]
    ]
    bq = FakeBigQueryReader({"FROM `p.d.courses`": pages})
    target = FakeCosmosContainer(name="courses")

    def factory(name: str) -> BatchWriter:
        return BatchWriter(target, concurrency=4)  # type: ignore[arg-type]

    runner = SyncRunner(
        bq_dataset=bq,  # type: ignore[arg-type]
        get_writer=factory,
        checkpoint_store=CheckpointStore(FakeCosmosContainer()),  # type: ignore[arg-type]
        pipelines=[default_registry().build("courses")],
        project_id="p",
        dataset="d",
    )
    summary = await runner.run()
    assert summary.status == "partial"
    assert summary.rows_read == 2
    assert summary.rows_upserted == 1
    assert summary.rows_failed == 1
