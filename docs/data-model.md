# data-model

LearnSphere is the sample domain. Five normalized BigQuery tables; three
denormalized Cosmos containers. Joins happen in SQL.

## BigQuery — `learnsphere` dataset

### `learners`

| column | type | notes |
| --- | --- | --- |
| `learner_id` | STRING (req) | stable identity |
| `email` | STRING (req) | unique per learner |
| `display_name` | STRING | |
| `country` | STRING | ISO-3166 alpha-2, drives Cosmos PK |
| `signup_date` | DATE | |
| `plan_tier` | STRING | `free` / `pro` / `team` |
| `updated_at` | TIMESTAMP (req) | bumped on any profile change |

### `instructors`

`instructor_id` (req), `display_name`, `bio`, `country`, `rating` (FLOAT64),
`updated_at` (req).

### `courses`

`course_id` (req), `title`, `category` (drives Cosmos PK), `level`
(`beginner`/`intermediate`/`advanced`), `duration_minutes` (INT64),
`price_usd` (FLOAT64), `instructor_id` (FK → `instructors`),
`updated_at` (req).

### `enrollments`

`enrollment_id` (req), `learner_id` (FK), `course_id` (FK), `enrolled_at`,
`progress_percent` (0–100), `status` (`active`/`completed`/`dropped`),
`last_activity_at` (drives the `learners` effective watermark).

### `course_reviews`

`review_id` (req), `course_id` (FK), `learner_id` (FK), `rating` (1–5),
`comment`, `created_at`.

## Cosmos — `learnsphere` database

### `courses` — PK `/category`, refresh `full`

`courses ⨝ instructors ⨝ agg(course_reviews)`. One read returns everything a
course-detail page needs.

```jsonc
{
  "id": "course::C-00042",
  "courseId": "C-00042",
  "category": "tech",
  "title": "Distributed Systems 101",
  "level": "intermediate",
  "durationMinutes": 90,
  "priceUsd": 19.99,
  "instructor": {
    "instructorId": "I-0007", "displayName": "Ada Lovelace",
    "bio": "...", "country": "GB", "rating": 4.78
  },
  "reviewStats": { "reviewCount": 132, "averageRating": 4.52 },
  "recentReviews": [{ "reviewId": "...", "rating": 5, "comment": "..." }],
  "sourceUpdatedAt": "...",
  "syncRunId": "..."
}
```

Category cardinality is 5–20, partitions stay balanced. The catalog is small
enough (≤ 100k rows) that full refresh is cheaper than incremental bookkeeping.

### `learners` — PK `/country`, refresh `incremental`

`learners ⨝ agg(enrollments ⨝ courses)`. Embeds stats and the 10 most recent
enrollments.

Watermark column: `effective_updated_at = GREATEST(learners.updated_at, MAX(enrollments.last_activity_at))`.
A learner whose enrollment progresses gets re-shipped even if their profile
row didn't change.

```jsonc
{
  "id": "learner::L-00123",
  "learnerId": "L-00123",
  "country": "US",
  "email": "...", "displayName": "...",
  "signupDate": "...", "planTier": "pro",
  "enrollmentStats": { "totalEnrolled": 7, "totalCompleted": 3, "averageProgress": 64.3 },
  "recentEnrollments": [{ "courseId": "...", "status": "active", "progressPercent": 80.0 }],
  "sourceUpdatedAt": "...",
  "effectiveUpdatedAt": "...",
  "syncRunId": "..."
}
```

### `recommendations` — PK `/learnerId`, refresh `full`

Computed in SQL from `enrollments` + `courses`. No source table — preferred
category by minutes consumed, ranked by global course popularity, excluding
already-enrolled.

```jsonc
{
  "id": "rec::L-00123",
  "learnerId": "L-00123",
  "recommendations": [
    { "courseId": "C-00088", "title": "...", "category": "tech",
      "level": "advanced", "score": 412.0, "rank": 1 }
  ],
  "generatedAt": "...",
  "syncRunId": "..."
}
```

Reads are always by single learner id → every read is a point read.

### `sync_metadata` — PK `/pipeline`

Operational only. One doc per (run, pipeline). Holds `run_id`, `status`,
row counts, `duration_ms`, `watermark`, timestamps, error. See
[observability.md](observability.md).
