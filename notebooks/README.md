# LearnSphere notebooks

End-to-end walkthrough of the sample domain that ships with this template.

## Layout

| Folder | Purpose |
| --- | --- |
| [bigquery](bigquery/) | Provision the LearnSphere dataset in BigQuery and seed it with deterministic fake data. |
| [cosmosdb](cosmosdb/) | Inspect the materialized documents in Cosmos DB after a sync run. |

## Recommended order

1. `bigquery/01_setup_dataset.ipynb` — create the dataset and the five source tables (`learners`, `instructors`, `courses`, `enrollments`, `course_reviews`).
2. `bigquery/02_seed_data.ipynb` — generate deterministic fake data with Faker and stream it into the five tables.
3. `bigquery/03_validate.ipynb` — run the same JOINs the sync pipelines do, locally, to confirm the dataset is healthy *before* you ship a job.
4. Run the sync (`docker compose up --build` or `azd up`).
5. `cosmosdb/01_inspect_containers.ipynb` — page through the three target containers and assert the materialized shape.
6. `cosmosdb/02_sync_metadata.ipynb` — read the per-run summaries from `sync_metadata` to confirm health and watermark progression.

## Environment

All notebooks read configuration from a `.env` file at the repo root (see [`.env.example`](../.env.example)). They use the same `google-cloud-bigquery` and `azure-cosmos` SDKs the production app uses — no shadow ORM.

```bash
uv sync --project py/apps/bq-cosmos-sync
uv run --project py/apps/bq-cosmos-sync jupyter lab
```

The notebooks pull their dependencies from the app's `pyproject.toml`, so `jupyter`, `faker`, `pandas`, and `python-dotenv` are all pinned alongside the runtime deps.
