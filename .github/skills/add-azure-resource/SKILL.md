---
name: add-azure-resource
description: 'Adds a new Azure resource to the Terraform infrastructure. Use when provisioning a new Azure service, adding a resource to Terraform, or extending cloud infrastructure.'
argument-hint: 'Describe the resource (e.g., "Azure Redis Cache", "Azure Key Vault", "Azure Service Bus")'
---

## Purpose
Step-by-step workflow for adding a new Azure resource as a reusable Terraform module.

## When to Use
- Adding a new Azure service (Redis, Service Bus, Storage Account, etc.).
- Extending infrastructure with optional resources.
- Wiring a new resource into the application runtime.

## Flow

1. **Create a new module** at `infra/modules/{resource-name}/main.tf`:
   - Each module is a single `main.tf` with variables, resources, and outputs:
     ```hcl
     # --- Variables ---
     variable "name" {
       description = "Resource name"
       type        = string
     }

     variable "resource_group_name" {
       description = "Resource group name"
       type        = string
     }

     variable "location" {
       description = "Azure region"
       type        = string
     }

     variable "tags" {
       description = "Resource tags"
       type        = map(string)
       default     = {}
     }

     # --- Resources ---
     resource "azurerm_redis_cache" "this" {
       name                = var.name
       location            = var.location
       resource_group_name = var.resource_group_name
       capacity            = 1
       family              = "C"
       sku_name            = "Basic"
       tags                = var.tags
     }

     # --- Outputs ---
     output "id" {
       value = azurerm_redis_cache.this.id
     }

     output "hostname" {
       value = azurerm_redis_cache.this.hostname
     }
     ```

2. **Add a feature flag** in `infra/variables.tf`:
   ```hcl
   variable "enable_redis" {
     description = "Provision Redis Cache"
     type        = bool
     default     = false
   }
   ```

3. **Add a module block** in `infra/main.tf`:
   - Add resource name to `local.names` map.
   - Use `count` for optional resources:
   ```hcl
   module "redis" {
     count  = var.enable_redis ? 1 : 0
     source = "./modules/redis"

     name                = local.names.redis
     resource_group_name = azurerm_resource_group.this.name
     location            = azurerm_resource_group.this.location
     tags                = local.tags
   }
   ```

4. **Add outputs** in `infra/outputs.tf` using `AZURE_*` naming:
   ```hcl
   output "AZURE_REDIS_HOSTNAME" {
     description = "Redis Cache hostname"
     value       = var.enable_redis ? module.redis[0].hostname : ""
   }
   ```

5. **Wire to app** (if needed):
   - Add env var to backend `env_vars` list in `infra/main.tf`.
   - Add setting to `AppSettings` in `core/config.py`.
   - Update `.env.example` and `.env.azure.example`.

6. **For RBAC access**, pass managed identity principal ID:
   ```hcl
   module "redis" {
     # ...
     access_principal_ids = [
       azurerm_user_assigned_identity.backend.principal_id,
     ]
   }
   ```

7. **Validate**:
   ```bash
   cd infra
   terraform init -backend=false
   terraform fmt -recursive
   terraform validate
   ```

## Decision Logic
- **App-consumed resource** (Redis, Service Bus): add outputs + wire to env vars.
- **Infra-only resource** (VNet, NSG): add resource + variables, no app wiring needed.
- **RBAC access**: add `principal_ids` variable to module, create role assignment internally.

## Checklist
- [ ] Module created in `infra/modules/{name}/main.tf`
- [ ] Feature flag variable added (`enable_{name}`)
- [ ] Module block added in root `main.tf` with naming and tags
- [ ] Outputs use `AZURE_*` naming convention
- [ ] `terraform fmt -recursive` passes
- [ ] `terraform validate` passes
- [ ] Environment files updated (if app-consumed)
- [ ] App config updated (if applicable)
