# deployment

`azd up` from a clean clone provisions everything and ships the first run.

## What gets provisioned

Single resource group:

- Container Apps Environment (vnet-integrated, wired to Log Analytics)
- Container App Job (cron, scale-to-zero)
- Container Registry (Premium, Private Endpoint, MI pull only)
- Cosmos DB for NoSQL — `local_authentication_disabled = true`, zone-redundant,
  continuous backup (PITR), Private Endpoint only, account + database +
  four containers
- Log Analytics workspace + Application Insights, plus a diagnostic setting
  on Cosmos streaming `DataPlaneRequests` / `QueryRuntimeStatistics` /
  `PartitionKey*` logs
- Key Vault (private, RBAC, holds the GCP SA JSON)
- VNet (10.20.0.0/16) with `snet-cae` (delegated, NSG) and `snet-pe` (NSG)
- NAT Gateway + Standard Public IP for deterministic egress to BigQuery
- Private DNS zones for `documents.azure.com`, `vaultcore.azure.net`,
  `azurecr.io` — linked to the vnet
- User-assigned managed identity (Cosmos data RBAC, AcrPull, KV Secrets Officer)
- 4 alert rules — see [observability.md](observability.md)

End-to-end identity story: [identity.md](identity.md).
End-to-end network story: [networking.md](networking.md).

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
2. The **secret-bootstrap** Container App Job runs once inside the vnet,
   reading the SA JSON from a Terraform-managed secret and writing it to
   the private Key Vault. This is how a private vault gets populated without
   ever opening its public endpoint to a developer laptop.
3. Docker build (multi-stage, non-root uid 1000) → push to ACR.
4. Container App Job updated to the new image.

After the first deploy, capture the egress IP to share with the BigQuery
owner so they can pin it in a VPC Service Controls perimeter or any other
network allow-list:

```bash
terraform -chdir=infra output -raw NAT_GATEWAY_EGRESS_IP
```

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
  Production target is [Workload Identity Federation](../examples/wif/),
  which eliminates this last long-lived credential.
- Cosmos: **no key**. The account ships with shared-key auth disabled.
  The MI uses a custom data-plane role on the account.
- ACR: no admin user. The MI has `AcrPull`.

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
