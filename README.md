# bigquery-cosmos-sync-job

Daily BigQuery → Cosmos DB (NoSQL) sync, packaged as an Azure Container App
Job. Cron-triggered, scale-to-zero, idempotent.

```
BigQuery ─► Container App Job (Python, async) ─► Cosmos DB (NoSQL)
                       │
                       └─► Log Analytics + App Insights
```

Use it when BigQuery holds the analytical truth and Cosmos is the serving
layer for an app — chat memory, recommendations, point lookups.

## Layout

| path | what |
| --- | --- |
| [py/apps/bq-cosmos-sync](py/apps/bq-cosmos-sync) | the job: Python 3.12, async, pluggable pipelines |
| [py/libs/bigquerykit](py/libs/bigquerykit) | async BigQuery I/O kit |
| [py/libs/cosmosdbkit](py/libs/cosmosdbkit) | async Cosmos DB I/O kit |
| [infra](infra) | Terraform (Container App Job, Cosmos, Key Vault, Log Analytics, App Insights, alerts) |
| [notebooks](notebooks) | LearnSphere sample: seed BQ, validate, inspect Cosmos |
| [docs](docs) | architecture, decisions, setup, deploy, observability, runbook |

Sample domain is **LearnSphere**: five normalized BigQuery tables
(`learners`, `instructors`, `courses`, `enrollments`, `course_reviews`)
joined in SQL into three denormalized Cosmos containers (`courses`,
`learners`, `recommendations`). Joins and aggregations live in SQL; Python
projects rows into documents. Swap the domain by replacing the pipelines.

## What this template gives you

A polished, enterprise-ready answer to the two questions every customer
asks first when moving data from BigQuery to Cosmos:

- **Identity.** One user-assigned managed identity, end to end. Cosmos
  ships with `local_authentication_disabled = true` (no shared keys), ACR
  admin is off, Key Vault is RBAC + private. The only long-lived credential
  is the GCP service-account JSON, and there's a drop-in
  [Workload Identity Federation example](examples/wif/) to delete that too.
  → [docs/identity.md](docs/identity.md)
- **Networking.** Cosmos, Key Vault, and ACR are reached over Private
  Endpoints. The Container Apps environment is vnet-integrated. Outbound
  to BigQuery exits through a NAT Gateway with a stable public IP that the
  BigQuery side can pin in a VPC Service Controls perimeter — the IP is
  the `NAT_GATEWAY_EGRESS_IP` Terraform output. NSGs on both subnets.
  → [docs/networking.md](docs/networking.md)

## Quick start

```bash
uv sync --project py/apps/bq-cosmos-sync          # install
cp .env.example .env && $EDITOR .env              # configure
uv run --project py/apps/bq-cosmos-sync jupyter lab notebooks/  # seed BQ
docker compose up --build                         # run vs. Cosmos emulator
azd up                                            # deploy to Azure
```

Full walk-through: [docs/setup.md](docs/setup.md).
Deploy: [docs/deployment.md](docs/deployment.md).

## Pipelines

`Pipeline` is a small protocol (`build_query`, `row_to_document`, optional
`extract_watermark`). The runner owns batching, retries, error isolation,
telemetry, and checkpoints — the pipeline file is just SQL + projection.

| pipeline | refresh | BQ source | container | PK |
| --- | --- | --- | --- | --- |
| `courses` | full | `courses ⨝ instructors ⨝ agg(course_reviews)` | `courses` | `/category` |
| `learners` | incremental on `effective_updated_at` | `learners ⨝ agg(enrollments ⨝ courses)` | `learners` | `/country` |
| `recommendations` | full | derived from `enrollments + courses` | `recommendations` | `/learnerId` |

`effective_updated_at = GREATEST(learners.updated_at, MAX(enrollments.last_activity_at))`
so a learner re-syncs on enrollment activity, not just profile edits.

Schemas, embeds, and PK rationale: [docs/data-model.md](docs/data-model.md).
Architecture and failure model: [docs/architecture.md](docs/architecture.md).
Adding a pipeline: [docs/extending.md](docs/extending.md).

## Observability

- structured JSON logs → Log Analytics (`ContainerAppConsoleLogs_CL`)
- OpenTelemetry traces → App Insights (when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set)
- one summary doc per (run, pipeline) in the `sync_metadata` Cosmos container
- five provisioned alerts: job failed, partial failure, missing daily success,
  abnormal row volume, sustained Cosmos 429 throttling

KQL queries, alert thresholds, and "healthy looks like":
[docs/observability.md](docs/observability.md).
When things break: [docs/troubleshooting.md](docs/troubleshooting.md).

## License

[MIT](LICENSE)
