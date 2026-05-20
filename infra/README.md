# Infrastructure

Terraform modules and azd configuration for deploying to Azure.

## Structure

```
infra/
├── main.tf              ← Root composition (resource group, identity, module calls)
├── provider.tf          ← Azure provider configuration
├── variables.tf         ← Root variables (subscription, region, feature flags)
├── outputs.tf           ← Root outputs (AZURE_* naming for azd)
├── backend.tf           ← State backend configuration
├── main.tfvars.example  ← Example variable values
├── scripts/
│   └── postprovision.sh ← Runs after azd provision
└── modules/
    ├── log-analytics/           ← Log Analytics workspace
    ├── application-insights/    ← App Insights + connection string
    ├── container-registry/      ← ACR + AcrPull RBAC
    ├── container-apps-environment/ ← CAE linked to logs
    ├── container-app/           ← Reusable per-app (backend, frontend)
    ├── cosmos-db/               ← Account + DB + containers + RBAC
    └── key-vault/               ← Key Vault + RBAC roles
```

## Resources Provisioned

| Resource | Module | Feature Flag |
|----------|--------|-------------|
| Resource Group | root | always |
| User-Assigned Managed Identity | root | always |
| Log Analytics Workspace | `log-analytics` | always |
| Application Insights | `application-insights` | always |
| Container Registry | `container-registry` | always |
| Container App Environment | `container-apps-environment` | always |
| Backend Container App | `container-app` | always |
| Frontend Container App | `container-app` | always |
| Cosmos DB | `cosmos-db` | `enable_cosmos_db` |
| Key Vault | `key-vault` | `enable_key_vault` |

## Naming Convention

Names are derived from `local.names` in root `main.tf` using `environment_name` + hash suffix:

| Variable | Default | Description |
|----------|---------|-------------|
| `environment_name` | `dev` | Used in all resource names |
| `location` | `eastus` | Azure region |
| `subscription_id` | (required) | Azure subscription ID |

## Usage

```bash
# First time: configure variables
cp infra/main.tfvars.example infra/main.tfvars
# Edit infra/main.tfvars with your subscription_id

# Provision infrastructure
azd provision

# Deploy application
azd deploy

# Or do both at once
azd up

# Validate changes
cd infra && terraform init -backend=false && terraform validate
```

## Adding a New Azure Resource

1. Create `infra/modules/{name}/main.tf` (variables + resources + outputs in one file).
2. Add `module` block in root `main.tf` — use feature flag (`count`) if optional.
3. Add `enable_{name}` variable in `variables.tf`.
4. Wire outputs to `outputs.tf` using `AZURE_*` naming.
5. Pass managed identity principal ID for RBAC if the app needs access.
6. Run `terraform fmt -recursive && terraform validate`.
