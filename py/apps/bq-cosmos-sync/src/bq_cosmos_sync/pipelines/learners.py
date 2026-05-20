"""learners ⨝ agg(enrollments ⨝ courses), incremental on effective_updated_at."""

from datetime import datetime
from typing import Any

from bq_cosmos_sync.pipelines.base import Pipeline, PipelineContext


class LearnersPipeline(Pipeline):
    name = "learners"
    container_name = "learners"
    partition_key_field = "country"
    refresh_mode = "incremental"
    watermark_column = "effective_updated_at"

    def build_query(self, ctx: PipelineContext) -> str:
        watermark_filter = ""
        if ctx.watermark is not None:
            watermark_filter = f"WHERE effective_updated_at >= TIMESTAMP('{ctx.watermark.isoformat()}')"

        return f"""
        WITH learner_activity AS (
          SELECT
            learner_id,
            MAX(last_activity_at) AS max_activity
          FROM `{ctx.project_id}.{ctx.dataset}.enrollments`
          GROUP BY learner_id
        ),
        candidate_learners AS (
          SELECT
            l.learner_id,
            GREATEST(
              l.updated_at,
              COALESCE(la.max_activity, l.updated_at)
            ) AS effective_updated_at
          FROM `{ctx.project_id}.{ctx.dataset}.learners` l
          LEFT JOIN learner_activity la USING (learner_id)
        ),
        filtered AS (
          SELECT *
          FROM candidate_learners
          {watermark_filter}
        ),
        enrollment_summary AS (
          SELECT
            e.learner_id,
            COUNT(*) AS total_enrolled,
            SUM(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS total_completed,
            AVG(e.progress_percent) AS avg_progress,
            ARRAY_AGG(
              STRUCT(
                e.course_id,
                c.title,
                c.category,
                e.status,
                e.progress_percent,
                e.last_activity_at
              )
              ORDER BY e.last_activity_at DESC
              LIMIT 10
            ) AS recent_enrollments
          FROM `{ctx.project_id}.{ctx.dataset}.enrollments` e
          LEFT JOIN `{ctx.project_id}.{ctx.dataset}.courses` c
            ON c.course_id = e.course_id
          WHERE e.learner_id IN (SELECT learner_id FROM filtered)
          GROUP BY e.learner_id
        )
        SELECT
          l.learner_id,
          l.email,
          l.display_name,
          l.country,
          l.signup_date,
          l.plan_tier,
          l.updated_at,
          f.effective_updated_at,
          COALESCE(es.total_enrolled, 0)   AS total_enrolled,
          COALESCE(es.total_completed, 0)  AS total_completed,
          es.avg_progress,
          COALESCE(es.recent_enrollments, []) AS recent_enrollments
        FROM filtered f
        JOIN `{ctx.project_id}.{ctx.dataset}.learners` l USING (learner_id)
        LEFT JOIN enrollment_summary es USING (learner_id)
        ORDER BY f.effective_updated_at
        """

    def row_to_document(self, row: dict[str, Any], *, ctx: PipelineContext) -> dict[str, Any]:
        learner_id = str(row["learner_id"])
        country = (row.get("country") or "XX").upper()
        return {
            "id": f"learner::{learner_id}",
            "learnerId": learner_id,
            "country": country,
            "email": row.get("email"),
            "displayName": row.get("display_name"),
            "signupDate": _iso(row.get("signup_date")),
            "planTier": row.get("plan_tier"),
            "enrollmentStats": {
                "totalEnrolled": int(row.get("total_enrolled") or 0),
                "totalCompleted": int(row.get("total_completed") or 0),
                "averageProgress": _float(row.get("avg_progress")),
            },
            "recentEnrollments": [_enrollment(e) for e in (row.get("recent_enrollments") or [])],
            "sourceUpdatedAt": _iso(row.get("updated_at")),
            "effectiveUpdatedAt": _iso(row.get("effective_updated_at")),
            "source": "bigquery",
            "syncRunId": ctx.run_id,
        }

    def extract_watermark(self, row: dict[str, Any]) -> datetime | None:
        value = row.get("effective_updated_at")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None


def _enrollment(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "courseId": str(e["course_id"]),
        "title": e.get("title"),
        "category": e.get("category"),
        "status": e.get("status"),
        "progressPercent": _float(e.get("progress_percent")),
        "lastActivityAt": _iso(e.get("last_activity_at")),
    }


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
