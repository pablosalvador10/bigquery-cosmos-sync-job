# identity

The end-to-end identity model for this sample. **One workload identity, no
passwords on either side.**

## TL;DR

| Direction | Who | How |
| --- | --- | --- |
| Azure → Cosmos DB | User-assigned managed identity (MI) | Entra ID token + Cosmos data-plane RBAC (custom role). Shared keys are **disabled** on the account. |
| Azure → Key Vault | Same MI | `Key Vault Secrets User` (read) and `Officer` (bootstrap-only write). |
| Azure → Container Registry | Same MI | `AcrPull` role; admin user is disabled. |
| Azure → App Insights / Log Analytics | Same MI | Built-in Monitor RBAC. |
| Azure → BigQuery (default) | Service account JSON in Key Vault | Mounted into the job at `/secrets/gcp-sa-json`. **One long-lived credential in the system.** |
| Azure → BigQuery (production target) | Workload Identity Federation | MI → Google STS → 1-hour BigQuery token. No SA key. See [examples/wif/](../examples/wif/). |

## Why managed identity, not an app registration

App registrations require a client secret or certificate. Both need to be
rotated, stored somewhere safe, and revoked when compromised. Managed
identities are issued by the platform, have no rotatable credential, and
appear in the audit log as the **exact workload** that called the API rather
than "some app".

We only reach for an app registration when one of these is true:

- We need user-delegated OAuth (`acr_token`, on-behalf-of flows). We don't.
- We need Microsoft Graph permissions. We don't.

So: MI everywhere.

## Cosmos: AAD-only by IaC default

[infra/main.tf](../infra/main.tf) sets `local_authentication_disabled = true`
on the Cosmos account. The Cosmos DB SDK rejects any request that presents a
shared key; only AAD tokens issued for `https://<account>.documents.azure.com`
are accepted.

The MI is granted a custom data-plane role with these actions:

```
Microsoft.DocumentDB/databaseAccounts/readMetadata
Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*
Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*
```

scoped to the Cosmos account. Definition lives in
[infra/modules/cosmos-db/main.tf](../infra/modules/cosmos-db/main.tf).

The Python app uses `azure.identity.DefaultAzureCredential` which picks up
the MI inside Container Apps (`AZURE_CLIENT_ID` env var pins which MI when a
container has more than one assigned) and `az login` locally.

### Emulator escape hatch

The local Cosmos emulator only accepts the well-known shared key. The app
honours `COSMOS_EMULATOR_KEY` **only when the endpoint host is `localhost`,
`127.0.0.1`, or `cosmos-emulator`** (the docker-compose service name). Any
other endpoint with `COSMOS_EMULATOR_KEY` set causes `validate_runtime()`
to raise on startup. See
[`config.py`](../py/apps/bq-cosmos-sync/src/bq_cosmos_sync/config.py).

## Key Vault: private + RBAC

- `public_network_access_enabled = false` — only the vnet-integrated job
  and the bootstrap job can reach the vault.
- RBAC instead of access policies (`rbac_authorization_enabled = true`).
- Soft-delete on, purge protection off (sample default; flip on for prod).
- The MI gets `Key Vault Secrets Officer` so the **bootstrap job** (running
  inside the vnet) can write the GCP SA JSON. The **runtime** sync job
  references the secret through a Container App secret binding which only
  requires `Key Vault Secrets User` semantically; we give the same MI Officer
  for simplicity. Split into two MIs (bootstrap-MI vs runtime-MI) if you want
  the runtime to be strictly read-only.

## Container Registry: MI-only pull

- `admin_enabled = false`.
- The Container App Job's MI is granted `AcrPull` on the registry.
- The CAE registry binding (`registry_identity = MI`) means the runtime pulls
  images using the MI's token — no admin user, no service principal secret.
- ACR ships with a Private Endpoint and Premium SKU. Public network access
  defaults to **enabled** so `azd up` works frictionlessly; flip
  `acr_public_network_access_enabled = false` once your CI pushes from
  inside the vnet or via an ACR Tasks trusted-services exemption.

## BigQuery side: SA key today, WIF tomorrow

The default ships with a Google service account JSON stored in Key Vault and
mounted as a file at `/secrets/gcp-sa-json`. The `bootstrap` Container App
Job uploads the file to Key Vault from inside the vnet (Key Vault is
private), so a developer laptop never has to reach the vault directly.

This is **the one long-lived credential in the whole system** and the
obvious production weakness:

- Key rotation is manual.
- Default GCP service account keys have no expiry.
- GCP audit logs show the SA, not the Azure workload that used it.

The production target is **Workload Identity Federation** (Azure MI → Google
STS → 1-hour BigQuery token). The Python code doesn't change — `google-auth`
handles both flows behind the same `Credentials` interface — so the migration
is purely an IAM + config swap. A minimal example lives in
[examples/wif/](../examples/wif/).

### Forcing the migration

Set a 90-day expiry on the SA key when you generate it. That gives you a
hard deadline rather than a "we'll get to it" item. The migration steps:

1. Create a Workload Identity Pool + OIDC Provider in GCP, trusting
   `https://sts.windows.net/<tenant>/`.
2. Map the MI's `sub` claim (its object ID) to a GCP federated principal.
3. Grant the federated principal `roles/iam.workloadIdentityUser` on the
   BigQuery SA, plus `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`
   on the dataset.
4. Swap the mounted file at `/secrets/gcp-sa-json` for an `external_account`
   JSON config. No app code change required.
5. Delete the SA key in GCP. Delete the `gcp-bigquery-sa` Key Vault secret.

## Identity-flow diagram

```
┌──────────────────────────────────────────┐
│  Container App Job (sync)                │
│                                          │
│  identity: id-<env>-sync (UAMI)          │
│                                          │
│  AZURE_CLIENT_ID env → DefaultAzureCred  │
└────────┬────────────┬────────────┬───────┘
         │            │            │
         │ AAD token  │ AAD token  │ Reads SA JSON
         ▼            ▼            ▼ from mounted file
   ┌──────────┐  ┌──────────┐  ┌────────────────────┐
   │ Cosmos   │  │   ACR    │  │  GCP BigQuery      │
   │ (RBAC,   │  │ (AcrPull)│  │  via SA key  ──►   │
   │  no key) │  │          │  │  WIF target        │
   └──────────┘  └──────────┘  └────────────────────┘
```

## Verifying the model

```bash
# Cosmos local auth must be disabled
az cosmosdb show \
  --name <cosmos-name> --resource-group <rg> \
  --query disableLocalAuth -o tsv     # → true

# ACR admin must be disabled
az acr show --name <acr-name> --query adminUserEnabled -o tsv  # → false

# Sync MI must have AcrPull, Cosmos data-plane role, KV Secrets Officer
az role assignment list \
  --assignee <mi-principal-id> \
  --all -o table

# The Container App Job must reference the MI for both runtime + ACR pull
az containerapp job show \
  --name <job-name> --resource-group <rg> \
  --query "{identity:identity, registries:properties.configuration.registries}"
```
