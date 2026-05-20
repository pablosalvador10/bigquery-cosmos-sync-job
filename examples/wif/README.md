# Workload Identity Federation: Azure → Google Cloud

Minimal, self-contained example that swaps the long-lived GCP service-account
JSON key for **Workload Identity Federation**. With WIF, the sync job's Azure
managed identity exchanges its AAD token for a short-lived BigQuery access
token via Google STS. There is no rotatable credential anywhere.

This is the production target referenced in [docs/identity.md](../../docs/identity.md).

## What you need on the GCP side

1. The Azure tenant ID that issues tokens for the managed identity.
2. The managed identity's **object ID** (the value of `sub` in the AAD token).
3. The BigQuery service account email you want the Azure workload to
   impersonate (the existing `bigquery-sa@<project>.iam.gserviceaccount.com`
   from this repo's setup is fine).

## Terraform (Google side)

Run this with `gcloud auth application-default login` as a user with
`roles/iam.workloadIdentityPoolAdmin` on the GCP project. See
[`terraform/main.tf`](terraform/main.tf).

```bash
cd terraform
terraform init
terraform apply \
  -var "project_id=<gcp-project>" \
  -var "azure_tenant_id=<azure-tenant-guid>" \
  -var "azure_mi_object_id=<sync-mi-object-id>" \
  -var "bigquery_sa_email=bigquery-sa@<gcp-project>.iam.gserviceaccount.com"

terraform output external_account_json > external_account.json
```

That JSON is the **non-secret** credential config. Check it into Key Vault
(or just into your Container App secret store) and mount it where the SA
JSON used to live: `/secrets/gcp-sa-json`.

## App-side change (zero code)

`google-auth` recognises both `service_account` and `external_account` JSON
shapes transparently. `GOOGLE_APPLICATION_CREDENTIALS` continues to point at
`/secrets/gcp-sa-json`. The Python code in this repo doesn't change.

The `external_account` config tells `google-auth`:

1. Fetch an AAD token for the managed identity (`audience` is the WIF
   provider's full resource name).
2. POST it to Google STS to exchange for a federated token.
3. POST that to Google IAM to impersonate the BigQuery SA.
4. Use the resulting 1-hour BigQuery token for the API call.

See [`bq_smoke.py`](bq_smoke.py) for a five-line BigQuery smoke test that
proves the federation works.

## Cleanup once WIF is live

```bash
# Delete the GCP service-account key
gcloud iam service-accounts keys list \
  --iam-account=bigquery-sa@<project>.iam.gserviceaccount.com
gcloud iam service-accounts keys delete <key-id> \
  --iam-account=bigquery-sa@<project>.iam.gserviceaccount.com

# Delete the Key Vault secret
az keyvault secret delete --vault-name <kv> --name gcp-bigquery-sa
```

After this, the system has **zero long-lived credentials**.
