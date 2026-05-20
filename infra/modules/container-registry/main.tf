# --- Variables ---
variable "name" {
  description = "Container Registry name (must be globally unique, alphanumeric)"
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

variable "sku" {
  description = "ACR SKU. Premium is required for Private Endpoints and customer-managed keys."
  type        = string
  default     = "Premium"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.sku)
    error_message = "sku must be 'Basic', 'Standard', or 'Premium'."
  }
}

variable "admin_enabled" {
  description = "Enable admin user. Should be false in production; pull/push happens via Entra ID and managed identity."
  type        = bool
  default     = false
}

variable "public_network_access_enabled" {
  description = "If false, the registry only accepts traffic from private endpoints and trusted Microsoft services."
  type        = bool
  default     = true
}

variable "pull_identity_principal_ids" {
  description = "Principal IDs to grant AcrPull role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Resources ---
resource "azurerm_container_registry" "this" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.sku
  admin_enabled                 = var.admin_enabled
  public_network_access_enabled = var.public_network_access_enabled
  tags                          = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  count                = length(var.pull_identity_principal_ids)
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = var.pull_identity_principal_ids[count.index]
}

# --- Outputs ---
output "id" {
  value = azurerm_container_registry.this.id
}

output "login_server" {
  value = azurerm_container_registry.this.login_server
}
