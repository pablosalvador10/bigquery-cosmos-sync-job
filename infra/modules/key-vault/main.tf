# --- Variables ---
variable "name" {
  description = "Key Vault name (globally unique, 3-24 chars)"
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

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "admin_principal_ids" {
  description = "Principal IDs to grant Key Vault Administrator role"
  type        = list(string)
  default     = []
}

variable "secrets_user_principal_ids" {
  description = "Principal IDs to grant Key Vault Secrets User role (read-only)"
  type        = list(string)
  default     = []
}

variable "secrets_officer_principal_ids" {
  description = "Principal IDs to grant Key Vault Secrets Officer role (read/write)"
  type        = list(string)
  default     = []
}

variable "public_network_access_enabled" {
  description = "If false, the vault only accepts traffic from private endpoints"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Resources ---
resource "azurerm_key_vault" "this" {
  name                          = var.name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = var.public_network_access_enabled
  tags                          = var.tags
}

resource "azurerm_role_assignment" "admin" {
  count                = length(var.admin_principal_ids)
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.admin_principal_ids[count.index]
}

resource "azurerm_role_assignment" "secrets_user" {
  count                = length(var.secrets_user_principal_ids)
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.secrets_user_principal_ids[count.index]
}

resource "azurerm_role_assignment" "secrets_officer" {
  count                = length(var.secrets_officer_principal_ids)
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.secrets_officer_principal_ids[count.index]
}

# --- Outputs ---
output "id" {
  value = azurerm_key_vault.this.id
}

output "name" {
  value = azurerm_key_vault.this.name
}

output "uri" {
  value = azurerm_key_vault.this.vault_uri
}
