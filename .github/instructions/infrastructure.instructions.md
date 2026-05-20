---
description: Infrastructure conventions for Terraform and azd.
applyTo: 'infra/**'
---

# Infrastructure Conventions

## Module Architecture
- Each Azure service has its own reusable module under `infra/modules/`.
- Available modules: `log-analytics`, `application-insights`, `container-registry`, `container-apps-environment`, `container-app`, `cosmos-db`, `key-vault`.
- Each module is a single `main.tf` with variables, resources, and outputs.
- Root `main.tf` composes modules, wires outputs, and manages the resource group + managed identity.

## Naming Convention
- All names derived from `local.names` in root `main.tf`.
- Pattern: `{abbreviation}-{environment_name}` (e.g. `log-dev`, `cae-dev`).
- Globally unique resources append a 6-char hash suffix from subscription ID.

## Feature Flags
- Use `enable_cosmos_db`, `enable_key_vault`, etc. to conditionally provision resources.
- Conditional outputs: `var.enable_x ? module.x[0].output : ""`.

## Adding a New Azure Resource
1. Create `infra/modules/{name}/main.tf` (variables + resources + outputs).
2. Add a `module` block in root `main.tf` with feature flag if optional.
3. Add variable in `variables.tf` with default.
4. Wire outputs to `outputs.tf` with `AZURE_*` naming for azd.
5. If backend needs access, pass `azurerm_user_assigned_identity.backend.principal_id` for RBAC.
6. Update `.env.azure.example` and `AppSettings` in `core/config.py`.
7. Run `terraform fmt -recursive && terraform validate`.

## RBAC Pattern
- Use User-Assigned Managed Identity for all Azure access.
- Pass `principal_id` to modules for role assignments.
- Each module handles its own role definitions internally.

## Outputs
- Root outputs: `AZURE_*` or `SERVICE_*` naming (ALLCAPS for azd integration).
- Module outputs: lowercase (`id`, `endpoint`, `uri`) for internal references.

## azd Integration
- `azure.yaml` maps Terraform outputs to app env vars.
- `infra/scripts/postprovision.sh` runs after `azd provision`.

## Validation
- `terraform init -backend=false && terraform validate` for syntax.
- `terraform fmt -check -recursive` for formatting.
