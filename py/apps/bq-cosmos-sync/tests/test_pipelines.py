from datetime import UTC, datetime

from bq_cosmos_sync.pipelines.base import PipelineContext
from bq_cosmos_sync.pipelines.registry import default_registry


def _ctx(**overrides: object) -> PipelineContext:
    base: dict[str, object] = {
        "project_id": "p",
        "dataset": "d",
        "run_id": "r",
        "watermark": None,
    }
    base.update(overrides)
    return PipelineContext(**base)  # type: ignore[arg-type]


def test_registry_lists_three_default_pipelines() -> None:
    assert default_registry().names() == ["courses", "learners", "recommendations"]


# --------------------------------------------------------------------- courses


def test_courses_query_joins_instructors_and_reviews() -> None:
    p = default_registry().build("courses")
    sql = p.build_query(_ctx())
    assert "FROM `p.d.courses` c" in sql
    assert "LEFT JOIN `p.d.instructors` i" in sql
    assert "FROM `p.d.course_reviews`" in sql
    assert "ARRAY_AGG" in sql


def test_courses_projects_joined_row_to_document() -> None:
    p = default_registry().build("courses")
    row = {
        "course_id": "C-1",
        "title": "Intro",
        "category": "tech",
        "level": "beginner",
        "duration_minutes": 30,
        "price_usd": 9.99,
        "updated_at": None,
        "instructor": {
            "instructor_id": "I-1",
            "display_name": "Ada Lovelace",
            "bio": "OG",
            "country": "GB",
            "rating": 4.8,
        },
        "review_count": 2,
        "avg_rating": 4.5,
        "recent_reviews": [
            {"review_id": "R-1", "learner_id": "L-1", "rating": 5, "comment": "great", "created_at": None},
        ],
    }
    doc = p.row_to_document(row, ctx=_ctx())
    assert doc["id"] == "course::C-1"
    assert doc[p.partition_key_field] == "tech"
    assert doc["instructor"]["instructorId"] == "I-1"
    assert doc["reviewStats"] == {"reviewCount": 2, "averageRating": 4.5}
    assert doc["recentReviews"][0]["reviewId"] == "R-1"
    assert doc["syncRunId"] == "r"


def test_courses_handles_missing_instructor_gracefully() -> None:
    p = default_registry().build("courses")
    row = {
        "course_id": "C-9",
        "title": "Solo",
        "category": "tech",
        "level": "beginner",
        "duration_minutes": 10,
        "price_usd": None,
        "updated_at": None,
        "instructor": {"instructor_id": None},
        "review_count": 0,
        "avg_rating": None,
        "recent_reviews": [],
    }
    doc = p.row_to_document(row, ctx=_ctx())
    assert doc["instructor"] is None
    assert doc["recentReviews"] == []


# --------------------------------------------------------------------- learners


def test_learners_query_joins_enrollments_and_courses() -> None:
    p = default_registry().build("learners")
    sql = p.build_query(_ctx())
    assert "learner_activity" in sql
    assert "enrollment_summary" in sql
    assert "FROM `p.d.enrollments` e" in sql
    assert "LEFT JOIN `p.d.courses` c" in sql
    assert "ARRAY_AGG" in sql
    assert "WHERE effective_updated_at >=" not in sql


def test_learners_incremental_query_includes_watermark() -> None:
    p = default_registry().build("learners")
    ctx = _ctx(watermark=datetime(2026, 5, 1, tzinfo=UTC))
    sql = p.build_query(ctx)
    assert "WHERE effective_updated_at >= TIMESTAMP" in sql
    assert "2026-05-01" in sql


def test_learners_projects_aggregated_row() -> None:
    p = default_registry().build("learners")
    row = {
        "learner_id": "L-1",
        "email": "a@example.com",
        "display_name": "A",
        "country": "us",
        "signup_date": None,
        "plan_tier": "pro",
        "updated_at": None,
        "effective_updated_at": datetime(2026, 5, 19, tzinfo=UTC),
        "total_enrolled": 3,
        "total_completed": 1,
        "avg_progress": 42.5,
        "recent_enrollments": [
            {
                "course_id": "C-1",
                "title": "T1",
                "category": "tech",
                "status": "active",
                "progress_percent": 80.0,
                "last_activity_at": None,
            },
        ],
    }
    doc = p.row_to_document(row, ctx=_ctx())
    assert doc["id"] == "learner::L-1"
    assert doc[p.partition_key_field] == "US"
    assert doc["enrollmentStats"]["totalEnrolled"] == 3
    assert doc["enrollmentStats"]["totalCompleted"] == 1
    assert doc["enrollmentStats"]["averageProgress"] == 42.5
    assert doc["recentEnrollments"][0]["courseId"] == "C-1"
    assert doc["effectiveUpdatedAt"] == "2026-05-19T00:00:00+00:00"


def test_learners_extracts_effective_watermark() -> None:
    p = default_registry().build("learners")
    wm = p.extract_watermark({"effective_updated_at": datetime(2026, 5, 19, tzinfo=UTC)})
    assert wm == datetime(2026, 5, 19, tzinfo=UTC)


# -------------------------------------------------------------- recommendations


def test_recommendations_query_uses_enrollments_only() -> None:
    p = default_registry().build("recommendations")
    sql = p.build_query(_ctx())
    assert "preferred_category" in sql
    assert "already_enrolled" in sql
    assert "course_popularity" in sql
    assert "FROM `p.d.enrollments`" in sql
    assert "JOIN `p.d.courses` c" in sql


def test_recommendations_flattens_struct_array() -> None:
    p = default_registry().build("recommendations")
    row = {
        "learner_id": "L-1",
        "generated_at": None,
        "recommendations": [
            {
                "course_id": "C-1",
                "title": "T1",
                "category": "tech",
                "level": "beginner",
                "score": 100,
                "rank": 1,
            },
            {
                "course_id": "C-2",
                "title": "T2",
                "category": "tech",
                "level": "intermediate",
                "score": 80,
                "rank": 2,
            },
        ],
    }
    doc = p.row_to_document(row, ctx=_ctx())
    assert doc["id"] == "rec::L-1"
    assert doc[p.partition_key_field] == "L-1"
    assert len(doc["recommendations"]) == 2
    assert doc["recommendations"][0]["title"] == "T1"
    assert doc["recommendations"][0]["score"] == 100.0
