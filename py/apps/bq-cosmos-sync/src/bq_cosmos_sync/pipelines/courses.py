"""courses ⨝ instructors ⨝ agg(course_reviews)."""

from typing import Any

from bq_cosmos_sync.pipelines.base import Pipeline, PipelineContext


class CoursesPipeline(Pipeline):
    name = "courses"
    container_name = "courses"
    partition_key_field = "category"
    refresh_mode = "full"

    def build_query(self, ctx: PipelineContext) -> str:
        return f"""
        WITH review_stats AS (
          SELECT
            course_id,
            COUNT(*)        AS review_count,
            AVG(rating)     AS avg_rating,
            ARRAY_AGG(
              STRUCT(review_id, learner_id, rating, comment, created_at)
              ORDER BY created_at DESC
              LIMIT 5
            ) AS recent_reviews
          FROM `{ctx.project_id}.{ctx.dataset}.course_reviews`
          GROUP BY course_id
        )
        SELECT
          c.course_id,
          c.title,
          c.category,
          c.level,
          c.duration_minutes,
          c.price_usd,
          c.updated_at,
          STRUCT(
            i.instructor_id,
            i.display_name,
            i.bio,
            i.country,
            i.rating
          ) AS instructor,
          COALESCE(rs.review_count, 0) AS review_count,
          rs.avg_rating,
          COALESCE(rs.recent_reviews, []) AS recent_reviews
        FROM `{ctx.project_id}.{ctx.dataset}.courses` c
        LEFT JOIN `{ctx.project_id}.{ctx.dataset}.instructors` i
          ON i.instructor_id = c.instructor_id
        LEFT JOIN review_stats rs
          ON rs.course_id = c.course_id
        """

    def row_to_document(self, row: dict[str, Any], *, ctx: PipelineContext) -> dict[str, Any]:
        course_id = str(row["course_id"])
        category = row.get("category") or "uncategorized"
        instructor = row.get("instructor") or {}
        return {
            "id": f"course::{course_id}",
            "courseId": course_id,
            "category": category,
            "title": row.get("title"),
            "level": row.get("level"),
            "durationMinutes": row.get("duration_minutes"),
            "priceUsd": _float(row.get("price_usd")),
            "instructor": _instructor(instructor),
            "reviewStats": {
                "reviewCount": int(row.get("review_count") or 0),
                "averageRating": _float(row.get("avg_rating")),
            },
            "recentReviews": [_review(r) for r in (row.get("recent_reviews") or [])],
            "sourceUpdatedAt": _iso(row.get("updated_at")),
            "source": "bigquery",
            "syncRunId": ctx.run_id,
        }


def _instructor(s: dict[str, Any]) -> dict[str, Any] | None:
    if not s or s.get("instructor_id") is None:
        return None
    return {
        "instructorId": str(s["instructor_id"]),
        "displayName": s.get("display_name"),
        "bio": s.get("bio"),
        "country": s.get("country"),
        "rating": _float(s.get("rating")),
    }


def _review(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "reviewId": str(r["review_id"]),
        "learnerId": str(r["learner_id"]),
        "rating": int(r["rating"]) if r.get("rating") is not None else None,
        "comment": r.get("comment"),
        "createdAt": _iso(r.get("created_at")),
    }


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
