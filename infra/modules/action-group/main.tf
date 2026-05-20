# --- Variables ---
variable "name" {
  description = "Action Group name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "short_name" {
  description = "Short name used in SMS / email subject (<=12 chars)"
  type        = string
}

variable "email_receivers" {
  description = "List of email receivers"
  type = list(object({
    name  = string
    email = string
  }))
  default = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Resource ---
resource "azurerm_monitor_action_group" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  short_name          = substr(var.short_name, 0, 12)
  tags                = var.tags

  dynamic "email_receiver" {
    for_each = var.email_receivers
    content {
      name                    = email_receiver.value.name
      email_address           = email_receiver.value.email
      use_common_alert_schema = true
    }
  }
}

# --- Outputs ---
output "id" {
  value = azurerm_monitor_action_group.this.id
}

output "name" {
  value = azurerm_monitor_action_group.this.name
}
