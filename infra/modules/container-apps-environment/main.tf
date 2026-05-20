# --- Variables ---
variable "name" {
  description = "Container Apps Environment name"
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

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for Container Apps logging"
  type        = string
}

variable "infrastructure_subnet_id" {
  description = "Subnet ID for vnet-integrated CAE (must be delegated to Microsoft.App/environments). Null for non-vnet CAE."
  type        = string
  default     = null
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Resources ---
resource "azurerm_container_app_environment" "this" {
  name                       = var.name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  infrastructure_subnet_id   = var.infrastructure_subnet_id
  tags                       = var.tags
}

# --- Outputs ---
output "id" {
  value = azurerm_container_app_environment.this.id
}
