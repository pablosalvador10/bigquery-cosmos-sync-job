"""Top-N courses per learner, derived in SQL from enrollments + courses."""

from typing import Any

from bq_cosmos_sync.pipelines.base import Pipeline, PipelineContext


class RecommendationsPipeline(Pipeline):
    name = "recommendations"
    container_name = "recommendations"
    partition_key_field = "learnerId"
    refresh_mode = "full"

    top_n: int = 5

    def build_query(self, ctx: PipelineContext) -> str:
        return f"""
        WITH learner_category_minutes AS (
          SELECT
            e.learner_id,
            c.category,
            SUM(c.duration_minutes * SAFE_DIVIDE(e.progress_percent, 100.0)) AS minutes
          FROM `{ctx.project_id}.{ctx.dataset}.enrollments` e
          JOIN `{ctx.project_id}.{ctx.dataset}.courses` c
            ON c.course_id = e.course_id
          GROUP BY e.learner_id, c.category
        ),
        preferred_category AS (
          SELECT
            learner_id,
            category
          FROM (
            SELECT
              learner_id,
              category,
              ROW_NUMBER() OVER (
                PARTITION BY learner_id
                ORDER BY minutes DESC, category
              ) AS rk
            FROM learner_category_minutes
          )
          WHERE rk = 1
        ),
        already_enrolled AS (
          SELECT
            learner_id,
            ARRAY_AGG(DISTINCT course_id) AS course_ids
          FROM `{ctx.project_id}.{ctx.dataset}.enrollments`
          GROUP BY learner_id
        ),
        course_popularity AS (
          SELECT
            course_id,
            COUNT(*) AS enroll_count
          FROM `{ctx.project_id}.{ctx.dataset}.enrollments`
          GROUP BY course_id
        ),
        candidates AS (
          SELECT
            pc.learner_id,
            c.course_id,
            c.title,
            c.category,
            c.level,
            COALESCE(cp.enroll_count, 0) AS score,
            ROW_NUMBER() OVER (
              PARTITION BY pc.learner_id
              ORDER BY COALESCE(cp.enroll_count, 0) DESC, c.course_id
            ) AS rk
          FROM preferred_category pc
          JOIN `{ctx.project_id}.{ctx.dataset}.courses` c
            ON c.category = pc.category
          LEFT JOIN course_popularity cp
            ON cp.course_id = c.course_id
          LEFT JOIN already_enrolled ae
            ON ae.learner_id = pc.learner_id
          WHERE c.course_id NOT IN UNNEST(IFNULL(ae.course_ids, []))
        )
        SELECT
          learner_id,
          CURRENT_TIMESTAMP() AS generated_at,
          ARRAY_AGG(
            STRUCT(course_id, title, category, level, score, rk AS rank)
            ORDER BY rk
            LIMIT {self.top_n}
          ) AS recommendations
        FROM candidates
        WHERE rk <= {self.top_n}
        GROUP BY learner_id
        """

    def row_to_document(self, row: dict[str, Any], *, ctx: PipelineContext) -> dict[str, Any]:
        learner_id = str(row["learner_id"])
        recs_raw = row.get("recommendations") or []
        recs = [
            {
                "courseId": str(r["course_id"]),
                "title": r.get("title"),
                "category": r.get("category"),
                "level": r.get("level"),
                "score": _float(r.get("score")),
                "rank": int(r["rank"]) if r.get("rank") is not None else None,
            }
            for r in recs_raw
        ]
        return {
            "id": f"rec::{learner_id}",
            "learnerId": learner_id,
            "recommendations": recs,
            "generatedAt": _iso(row.get("generated_at")),
            "source": "bigquery",
            "syncRunId": ctx.run_id,
        }


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
