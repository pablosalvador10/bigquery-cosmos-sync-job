# --- Variables ---
variable "name" {
  description = "Cosmos DB account name (globally unique)"
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

variable "database_name" {
  description = "SQL database name"
  type        = string
}

variable "containers" {
  description = "List of containers to create"
  type = list(object({
    name               = string
    partition_key_path = string
    throughput         = optional(number)
  }))
  default = []
}

variable "role_assignment_principal_ids" {
  description = "Principal IDs to grant Cosmos data-plane read/write access"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Resources ---
resource "azurerm_cosmosdb_account" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  tags                = var.tags

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "this" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

resource "azurerm_cosmosdb_sql_container" "this" {
  count               = length(var.containers)
  name                = var.containers[count.index].name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths = [var.containers[count.index].partition_key_path]
  throughput          = var.containers[count.index].throughput
}

# Data-plane RBAC: custom role + assignment
resource "azurerm_cosmosdb_sql_role_definition" "readwrite" {
  count               = length(var.role_assignment_principal_ids) > 0 ? 1 : 0
  name                = "${var.name}-readwrite"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  type                = "CustomRole"
  assignable_scopes   = [azurerm_cosmosdb_account.this.id]

  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*",
    ]
  }
}

resource "azurerm_cosmosdb_sql_role_assignment" "this" {
  count               = length(var.role_assignment_principal_ids)
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.readwrite[0].id
  principal_id        = var.role_assignment_principal_ids[count.index]
  scope               = azurerm_cosmosdb_account.this.id
}

# --- Outputs ---
output "id" {
  value = azurerm_cosmosdb_account.this.id
}

output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.this.name
}
