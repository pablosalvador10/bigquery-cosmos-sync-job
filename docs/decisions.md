# decisions

The short version of choices a reader will second-guess. Long form lives in
commit history and PRs.

## Compute: Container App Job

Functions consumption plan times out at 10 min and has cold-start jitter that
shows up as flaky tail-latency at our run cadence. Logic Apps forces the data
model into the BigQuery connector's row shape. Container App Job runs any
image, scales to zero, supports user-assigned managed identity natively, and
has first-class azd support. The runner has no Container Apps dependency so
moving to AKS / Functions Premium later is a redeploy, not a rewrite.

## Joins in BigQuery, not Python

`build_query` is a string; `row_to_document` is a projection. Adding a
join means adding it to the SQL, not iterating in Python. We pay for one
shaped scan instead of N raw scans plus an in-memory join. Embeds use
`ARRAY_AGG(STRUCT(...) ORDER BY ... LIMIT N)` for bounded arrays.

If you ever need to join across heterogeneous sources (BQ + Postgres),
move the join out — but at that point the pipeline contract needs to
change to "return async row iterator" too.

## Deterministic ids, upserts only

`id = "<entity>::<source-pk>"`. Every write is an upsert. Re-runs are
idempotent. No tombstones unless you need hard deletes; the convention is to
filter `deleted_at` in `build_query` and add a separate tombstone pipeline.

## Watermark in `sync_metadata`, not Azure Storage

`sync_metadata` is already in the dependency graph. Reusing it removes a
Storage account, an IAM binding, and a failure mode. `CheckpointStore` is one
class — swap the backing container for Table Storage if you prefer.

## `learners` watermark = effective updated-at

If we used `learners.updated_at` directly, a learner who finishes a course
wouldn't trigger a profile re-sync (their profile row didn't change). The
SQL computes `GREATEST(learners.updated_at, MAX(enrollments.last_activity_at))`
so the embed refreshes on activity. Drop the CTE if you don't need
embed-on-activity behaviour.

## Two libraries, one app

`bigquerykit` and `cosmosdbkit` live as separate workspace packages. They're
reusable across other jobs; upgrading either SDK is a library bump rather
than an app change. Collapse them back into the app if the seam stops paying.

## Identity: managed identity, no app registration

The Container App Job runs as a user-assigned managed identity. That MI gets
RBAC on ACR (pull), Cosmos (custom data-plane role), and Key Vault (get
secret). An Entra ID app registration would be a step backwards here — it
adds a client secret or cert that has to be rotated, stored, and revoked,
and the audit trail becomes "some app" instead of "this exact job". The only
reasons to add an app registration would be (a) we needed user-delegated
OAuth, which we don't, or (b) Microsoft Graph API permissions, which we
don't. So: MI only.

See [identity.md](identity.md) for the full end-to-end identity story
(Cosmos local-auth-disabled, KV RBAC, ACR pull, the WIF migration path).

## Cosmos: AAD-only, local auth disabled

`local_authentication_disabled = true` on the Cosmos account. The SDK
rejects any shared-key request. This eliminates an entire class of
credential-leak incidents and forces every actor — runtime, developers,
notebooks — through Entra ID with auditable RBAC. The local Cosmos emulator
still works via a tightly-scoped `COSMOS_EMULATOR_KEY` env var that the app
refuses for any non-localhost endpoint.

## Networking: Private Endpoints + NAT Gateway

The default network model is what most security baselines require:

- Cosmos and Key Vault are reachable only through Private Endpoints.
- ACR is Premium with a Private Endpoint (public network access stays on
  by default so `azd up` works frictionlessly; flip
  `acr_public_network_access_enabled` to lock it down).
- Outbound to BigQuery exits through a Standard NAT Gateway with a Static
  Public IP, so the BigQuery side can pin one egress IP in a VPC Service
  Controls perimeter. The IP is the `NAT_GATEWAY_EGRESS_IP` output.
- NSGs on both subnets: snet-cae is deny-by-default outbound with explicit
  allows for AzureCloud:443 + Internet:443. snet-pe only accepts inbound
  443 from the vnet.

Customers who want a quicker path can flip the public-access switches and
add IP allow-lists — Pattern A in [networking.md](networking.md). The IaC
makes both patterns available with one variable each.

## GCP auth: SA-key today, WIF next

Today the pipeline authenticates to BigQuery with a long-lived service
account JSON key stored in Key Vault and mounted into the container at
`/secrets/gcp-sa-json`. This is the **one long-lived credential in the
whole system** and is the obvious production weakness — key rotation is
manual, the key has no expiry by default, and GCP audit logs show the SA
rather than the Azure workload that used it.

The production target is **Workload Identity Federation** (Azure MI →
GCP STS → 1-hour access token → BigQuery). No SA key, no Key Vault secret,
no rotation. With WIF the credential file becomes an `external_account`
JSON config (non-secret, can live in the repo), and we can use the MI's
own client ID as the OIDC audience — *still no separate app registration
needed*.

Shipping with the SA-key model first because:

- It works end-to-end on day one with no GCP IAM coordination required.
- The migration is mechanical: change `GOOGLE_APPLICATION_CREDENTIALS` to
  point at the `external_account` config, delete the KV secret, delete the
  SA key in GCP. The Python code doesn't change — `google-auth` handles
  both flows behind the same `Credentials` interface.
- Setting a 90-day expiry on the SA key forces rotation and gives us a
  hard deadline to do the WIF migration.

When you migrate: create a Workload Identity Pool in GCP, register an
OIDC provider that trusts `https://sts.windows.net/<tenant>/`, map the MI's
`sub` claim to a GCP federated principal, grant that principal
`roles/iam.workloadIdentityUser` on the BigQuery service account, swap the
mounted file. Then delete the SA key and the `gcp-bigquery-sa` Key Vault
secret.

## What's deliberately out

- No CDC. Batch only.
- No schema migration. Cosmos is schema-on-read.
- No hard deletes.
- No multi-region writes. Single-write region by default; Cosmos can flip to
  multi-region later without code changes.
