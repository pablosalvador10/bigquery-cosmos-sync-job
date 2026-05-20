# networking

The end-to-end network model for this sample. **Cosmos and Key Vault are
private. BigQuery has a stable egress IP.**

## TL;DR

| Concern | What ships in the IaC |
| --- | --- |
| Cosmos DB reachability | Private Endpoint only (`public_network_access_enabled = false`). |
| Key Vault reachability | Private Endpoint only. |
| Container Registry reachability | Premium SKU + Private Endpoint. Public access stays on by default for `azd up`; flip [`acr_public_network_access_enabled`](../infra/variables.tf) to `false` to lock it down. |
| BigQuery egress IP | Stable, single Standard public IP via NAT Gateway. Exposed as the [`NAT_GATEWAY_EGRESS_IP`](../infra/outputs.tf) output. |
| Subnet isolation | Two purpose-built subnets in a single /16. NSGs on both. |
| DNS for private endpoints | Private DNS zones linked to the vnet. SDK clients resolve transparently. |

## Topology

```
┌──────────────────────────── vnet-<env> (10.20.0.0/16) ─────────────────────────────┐
│                                                                                    │
│  ┌──── snet-cae (10.20.0.0/23) ────┐     ┌──── snet-pe (10.20.2.0/24) ────┐        │
│  │  delegated to Microsoft.App/    │     │  Private Endpoint NICs only:   │        │
│  │  environments                   │     │                                │        │
│  │                                 │     │   • PE → Cosmos (subres Sql)   │        │
│  │  Container Apps Environment     │     │   • PE → Key Vault (vault)     │        │
│  │   ├─ Sync job (cron)            │────▶│   • PE → ACR (registry)        │        │
│  │   └─ Bootstrap job (one-shot)   │     │                                │        │
│  │                                 │     │  NSG: only inbound 443         │        │
│  │  NSG: deny-by-default outbound  │     │  from VirtualNetwork           │        │
│  │   + allow 443→AzureCloud        │     └────────────────────────────────┘        │
│  │   + allow 443→Internet  ┐       │                                               │
│  └─────────────────────────│───────┘                                               │
│                            │                                                       │
│            ┌───────────────▼────────────┐                                          │
│            │ NAT Gateway (Standard)     │                                          │
│            │ + Standard Public IP       │   ── stable egress IP for BigQuery       │
│            │   (zonal: 1, 2, 3)         │      → goes on the GCP allow-list /      │
│            └────────────────────────────┘        VPC Service Controls perimeter    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Outbound to BigQuery (`bigquery.googleapis.com`, `storage.googleapis.com`) goes
**through the NAT Gateway**, so every TCP connection looks like it came from the
single Standard public IP. The GCP side can pin that IP in:

- a **BigQuery IAM condition** that requires `request.auth.access_levels`
  matching a VPC Service Controls access policy, or
- a perimeter on the BigQuery dataset, or
- a plain network allow-list on a fronting Cloud Run / API Gateway.

Hand the value of the `NAT_GATEWAY_EGRESS_IP` Terraform output to the BigQuery
owner. Re-run `terraform output NAT_GATEWAY_EGRESS_IP` any time.

## What's reachable from where

| From | To | How |
| --- | --- | --- |
| Sync job (CAE) | Cosmos DB | Private Endpoint via `privatelink.documents.azure.com`. |
| Sync job (CAE) | Key Vault (via Container App secret reference) | Private Endpoint via `privatelink.vaultcore.azure.net`. |
| Sync job (CAE) | ACR (image pull at startup) | Private Endpoint via `privatelink.azurecr.io`. |
| Sync job (CAE) | BigQuery | Public Internet, but egress IP is pinned by NAT Gateway. |
| Sync job (CAE) | App Insights / Log Analytics | AzureCloud service tag (PE-capable, not required for the sample). |
| Developer laptop | Cosmos / KV | **Cannot** reach them directly while `public_network_access_enabled = false`. Use the notebooks via `az login` + a jump host, an Azure Bastion + VM, or temporarily flip the public-access switch with an IP allow-list. |
| ACR Tasks (`az acr build` from `azd up`) | ACR | Public endpoint while `acr_public_network_access_enabled = true` (default). Flip to false + enable trusted-services bypass to fully privatise. |

## NSG rules in detail

### `nsg-cae-<env>` (on `snet-cae`)

| Priority | Direction | Action | Protocol | Dest port | Destination | Purpose |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | Outbound | Allow | TCP | 443 | `AzureCloud` | All Azure data-plane (Cosmos PE, KV PE, ACR PE, App Insights, AAD, ACR, MCR). |
| 110 | Outbound | Allow | TCP | 443 | `Internet` | BigQuery / Google Cloud APIs. Source IP is the NAT egress IP. |
| 120 | Outbound | Allow | Any | * | `VirtualNetwork` | Intra-vnet (PE NICs live here). |
| 4096 | Outbound | Deny | Any | * | * | Everything else. |

Container Apps Consumption platform requirements (TCP 443 to MCR, AAD,
AzureMonitor, AzureFrontDoor.FirstParty) are all covered by the
`AzureCloud` rule.

### `nsg-pe-<env>` (on `snet-pe`)

| Priority | Direction | Action | Protocol | Dest port | Source | Purpose |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | Inbound | Allow | TCP | 443 | `VirtualNetwork` | Sync job → PE NICs. |
| (default) | Inbound | Deny | Any | * | * | Nothing else can reach the PE NICs. |

## Private DNS zones

Three zones are pre-linked to the vnet so SDK calls to
`<acct>.documents.azure.com` / `<vault>.vault.azure.net` /
`<acr>.azurecr.io` resolve to the PE's private IP automatically:

- `privatelink.documents.azure.com`
- `privatelink.vaultcore.azure.net`
- `privatelink.azurecr.io`

If you bring your own DNS (Azure DNS Private Resolver, a forwarder in
on-prem), point the `privatelink.*` zones at the PE IPs you provision.

## Two networking patterns customers usually choose between

### Pattern A — public endpoints + IP allow-list (lowest effort)

Set `cosmos_public_network_access_enabled = true`, omit the PEs, and add
the developer laptop / CI runner IPs to the Cosmos and Key Vault firewall.
NSGs on `snet-cae` still constrain egress.

When this is enough:

- POC / pre-production environment.
- Single-team workload with no central network governance.
- You don't need to satisfy "no public endpoints" in your security baseline.

### Pattern B — Private Endpoints + NAT Gateway (this sample's default)

Everything above. Cosmos and KV are unreachable from the public Internet,
ACR has a PE, egress is pinned to one IP for BigQuery side allow-listing.

When this is the right answer:

- Enterprise security baseline requires private endpoints.
- BigQuery owner uses VPC Service Controls.
- You want one obvious networking surface to audit.

### Migrating from A to B

1. `terraform apply` with the defaults in this repo (creates all the network
   resources alongside the existing ones).
2. Flip the existing `azurerm_cosmosdb_account.public_network_access_enabled`
   to `false`. Cosmos clients inside the vnet keep working via the PE
   thanks to the private DNS zones.
3. Same for Key Vault and ACR.
4. Drop any public IP allow-list firewall rules.

## Operations

```bash
# Get the egress IP (give this to the BigQuery owner)
terraform output -raw NAT_GATEWAY_EGRESS_IP

# Verify the PEs are healthy
az network private-endpoint show -g <rg> -n pe-cosmos-<env> \
  --query "privateLinkServiceConnections[0].privateLinkServiceConnectionState"

# Confirm Cosmos / KV / ACR refuse public traffic
az cosmosdb show -g <rg> -n <cosmos-name> --query publicNetworkAccess  # → "Disabled"
az keyvault show -g <rg> -n <kv-name>     --query properties.publicNetworkAccess  # → "Disabled"
az acr show     -g <rg> -n <acr-name>     --query publicNetworkAccess  # → "Enabled" or "Disabled" depending on tfvar
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `azd up` fails on `az acr build`: `403 - The client ... is not authorized to perform action` | ACR PNA is disabled and you're not inside the vnet | Flip `acr_public_network_access_enabled = true`, or run `az acr build` from an Azure-hosted runner with the right trusted-services bypass. |
| Sync job times out resolving `*.documents.azure.com` | Private DNS zone is not linked to the vnet | Verify `azurerm_private_dns_zone_virtual_network_link.cosmos` is present. |
| BigQuery side reports calls from changing IPs | NAT Gateway not associated with `snet-cae` | Verify `azurerm_subnet_nat_gateway_association.cae` exists. The egress IP is in `terraform output NAT_GATEWAY_EGRESS_IP`. |
| Notebooks against private Cosmos fail with `name resolution failure` | Your laptop is not on the vnet | Run notebooks from an Azure VM / Bastion, or set `cosmos_public_network_access_enabled = true` and add your laptop IP. |
| CAE deployment fails with `subnet has insufficient address space` | `snet-cae` is smaller than /23 | The Container Apps Consumption profile requires at least /23. |
