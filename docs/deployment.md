# deployment

`azd up` from a clean clone provisions everything and ships the first run.

## What gets provisioned

Single resource group:

- Container Apps Environment (wired to Log Analytics)
- Container App Job (cron, scale-to-zero)
- Container Registry
- Cosmos DB for NoSQL (account, database, four containers)
- Log Analytics workspace + Application Insights
- Key Vault (holds the GCP SA JSON)
- User-assigned managed identity (granted Cosmos data-plane RBAC)
- 4 alert rules — see [observability.md](observability.md)

## First deploy

```bash
azd auth login
az login
azd init    # if not done already; reads azure.yaml
azd env set GCP_SA_JSON_PATH ./secrets/gcp-sa.json
azd up
```

Phases:

1. Terraform `apply`.
2. `infra/scripts/postprovision.sh` — uploads the SA JSON to Key Vault as
   `gcp-sa-json` (no dots — Container App secret rule), grants the job's
   managed identity Cosmos data RBAC, creates the four containers.
3. Docker build (multi-stage, non-root uid 1000) → push to ACR.
4. Container App Job updated to the new image.

## Day-2

| action | command |
| --- | --- |
| ship code | `azd deploy` |
| infra-only | `azd provision` |
| trigger ad-hoc run | `az containerapp job start -n <job> -g <rg>` |
| tail logs | `az containerapp job logs show -n <job> -g <rg> --follow` |
| teardown | `azd down --purge` |

## CI/CD

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs ruff, pyright,
pytest across the app + both kits, plus `terraform fmt -check` and
`terraform validate`. Wire deploys with an OIDC-federated service principal
(`azure/login@v2`) and `azd deploy --no-prompt` on push to `main`.

## Secrets

- GCP SA JSON → Key Vault secret `gcp-sa-json` → mounted at
  `/secrets/gcp-sa-json` → `GOOGLE_APPLICATION_CREDENTIALS` points there.
- Cosmos: no key. Managed identity → built-in
  `Cosmos DB Built-in Data Contributor` role on the account.

## Sizing

Sized for ~500 MB/day:

- Cosmos shared throughput 400 RU/s. Bump per container when you start seeing
  429s in `sync_metadata` (see [troubleshooting.md](troubleshooting.md)).
- Log Analytics on pay-as-you-go, 30-day retention.
- App Insights 100% sampling (low traffic).
- Job is scale-to-zero — you pay for the seconds it runs.

Scaling further: raise `BATCH_WRITER_CONCURRENCY`, `BQ_PAGE_SIZE`,
`SYNC_PARALLELISM`. Cosmos partition keys and BQ slot quotas are the limits
that matter.
