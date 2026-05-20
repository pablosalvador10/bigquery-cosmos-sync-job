# Azure Resource Reference

## Terraform Module Structure

```
infra/
├── main.tf              # Root composition — modules, identity, resource group
├── provider.tf          # Azure provider config
├── variables.tf         # Root variables + feature flags
├── outputs.tf           # Root outputs (AZURE_* for azd)
├── backend.tf           # State backend config
├── main.tfvars.example  # Example variable values
├── scripts/
│   └── postprovision.sh # Post-deployment setup
└── modules/
    ├── log-analytics/           # Log Analytics workspace
    ├── application-insights/    # App Insights
    ├── container-registry/      # ACR + AcrPull RBAC
    ├── container-apps-environment/ # CAE
    ├── container-app/           # Reusable per-app
    ├── cosmos-db/               # Account + DB + containers + RBAC
    └── key-vault/               # Key Vault + RBAC
```

## Resource Naming Convention

Names are derived from `local.names` in root `main.tf`:
- Pattern: `{abbreviation}-{environment_name}` (e.g. `log-dev`, `cae-dev`)
- Globally unique resources append a 6-char hash suffix

| Variable | Default | Purpose |
|----------|---------|---------|
| `environment_name` | `dev` | Used in all resource names |
| `location` | `eastus` | Azure region |

## Provisioned Resources

### Always Provisioned
| Resource | Module | Purpose |
|----------|--------|---------|
| Resource Group | root | Container for all resources |
| Managed Identity | root | RBAC access to Azure services |
| Log Analytics | `log-analytics` | Centralized logging |
| Application Insights | `application-insights` | APM + tracing |
| Container Registry | `container-registry` | Container image storage |
| Container App Environment | `container-apps-environment` | Hosting environment |
| Backend Container App | `container-app` | Backend API |
| Frontend Container App | `container-app` | Chat UI |

### Conditional (Feature Flags)
| Resource | Module | Flag |
|----------|--------|------|
| Cosmos DB | `cosmos-db` | `enable_cosmos_db` |
| Key Vault | `key-vault` | `enable_key_vault` |

## Outputs

| Output | Source | Consumed By |
|--------|--------|-------------|
| `SERVICE_BACKEND_URI` | Container App | Frontend API config |
| `SERVICE_FRONTEND_URI` | Container App | User access |
| `AZURE_COSMOS_ENDPOINT` | Cosmos DB | Backend storage config |
| `AZURE_APPINSIGHTS_CONNECTION_STRING` | App Insights | Backend telemetry |
| `AZURE_CONTAINER_REGISTRY_LOGIN_SERVER` | ACR | CI/CD image push |
| `AZURE_MANAGED_IDENTITY_CLIENT_ID` | Managed Identity | Backend auth |

## Adding a New Resource

1. Create `infra/modules/{name}/main.tf` (variables + resources + outputs)
2. Add `enable_{name}` feature flag in `variables.tf`
3. Add module block in root `main.tf` with `count` and naming
4. Pass managed identity principal ID for RBAC
5. Wire outputs using `AZURE_*` naming in `outputs.tf`
6. Update `.env.azure.example` with new env vars
7. Run `terraform fmt -recursive && terraform validate`

## Common Patterns

### RBAC Role Assignment (inside module)
```hcl
variable "role_assignment_principal_ids" {
  type    = list(string)
  default = []
}

resource "azurerm_role_assignment" "this" {
  count                = length(var.role_assignment_principal_ids)
  scope                = azurerm_resource.this.id
  role_definition_name = "Contributor"
  principal_id         = var.role_assignment_principal_ids[count.index]
}
```

### Conditional Module Output
```hcl
output "AZURE_REDIS_HOSTNAME" {
  value = var.enable_redis ? module.redis[0].hostname : ""
}
```
