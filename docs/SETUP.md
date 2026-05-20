# setup

Local dev loop. Install deps, seed BigQuery, point the sync at the emulator
or a real account.

## Prereqs

Python 3.12, [uv](https://docs.astral.sh/uv/), Docker, Terraform ≥ 1.6,
[azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/),
`gcloud`, `az`.

## Install

```bash
uv sync --project py/apps/bq-cosmos-sync
```

Resolves the whole workspace (app + both kits) in one go.

## Configure

```bash
cp .env.example .env
$EDITOR .env
```

| var | purpose |
| --- | --- |
| `BQ_PROJECT_ID` | GCP project |
| `BQ_DATASET` | default `learnsphere` |
| `BQ_LOCATION` | default `US` |
| `GOOGLE_APPLICATION_CREDENTIALS` | path to GCP SA JSON; mounted at `/secrets/gcp-sa-json` in the image |
| `COSMOS_ENDPOINT` | account URL, or `https://localhost:8081/` for the emulator |
| `COSMOS_EMULATOR_KEY` | **emulator-only escape hatch** — refused for any non-localhost endpoint. Production uses Microsoft Entra ID (managed identity in Azure, `az login` locally). |
| `COSMOS_DATABASE` | default `learnsphere` |
| `SYNC_PIPELINES` | comma-separated, default `courses,learners,recommendations` |

The IaC ships with `local_authentication_disabled = true` on the Cosmos
account, so shared keys are rejected in production no matter what env vars
are set. See [identity.md](identity.md) for the full identity story.

## GCP service account

```bash
gcloud iam service-accounts create bq-cosmos-sync-reader \
  --display-name "BQ → Cosmos sync reader"

for role in roles/bigquery.dataViewer roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding "$BQ_PROJECT_ID" \
    --member "serviceAccount:bq-cosmos-sync-reader@${BQ_PROJECT_ID}.iam.gserviceaccount.com" \
    --role "$role"
done

gcloud iam service-accounts keys create ./secrets/gcp-sa.json \
  --iam-account "bq-cosmos-sync-reader@${BQ_PROJECT_ID}.iam.gserviceaccount.com"
```

`secrets/` is gitignored.

## Seed BigQuery

```bash
uv sync --project py/apps/bq-cosmos-sync --group notebooks
uv run --project py/apps/bq-cosmos-sync jupyter lab notebooks/
```

Run in order:

1. `bigquery/01_setup_dataset.ipynb`
2. `bigquery/02_seed_data.ipynb`
3. `bigquery/03_validate.ipynb`

## Run

Against the emulator:

```bash
docker compose up --build
```

Against a real account:

```bash
uv run --project py/apps/bq-cosmos-sync bq-cosmos-sync run
```

CLI:

```bash
bq-cosmos-sync run --help
bq-cosmos-sync run --pipeline learners --dry-run
bq-cosmos-sync run --pipeline courses --max-rows 100
```

## Validate

```bash
uv run --project py/apps/bq-cosmos-sync jupyter lab notebooks/
# cosmosdb/01_inspect_containers.ipynb
# cosmosdb/02_sync_metadata.ipynb
```

Or with az:

```bash
az cosmosdb sql query \
  --account-name <acc> --database-name learnsphere \
  --container-name sync_metadata \
  --query-text "SELECT TOP 5 * FROM c ORDER BY c.finished_at DESC"
```
