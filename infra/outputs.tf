output "AZURE_RESOURCE_GROUP_NAME" {
  description = "Resource group name"
  value       = azurerm_resource_group.this.name
}

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  description = "ACR login server"
  value       = module.acr.login_server
}

output "SERVICE_BACKEND_URI" {
  description = "Backend Container App URL"
  value       = module.backend.uri
}

output "SERVICE_FRONTEND_URI" {
  description = "Frontend Container App URL"
  value       = module.frontend.uri
}

output "AZURE_COSMOS_ENDPOINT" {
  description = "Cosmos DB endpoint (empty if disabled)"
  value       = var.enable_cosmos_db ? module.cosmos[0].endpoint : ""
}

output "AZURE_APPINSIGHTS_CONNECTION_STRING" {
  description = "Application Insights connection string"
  value       = module.appinsights.connection_string
  sensitive   = true
}

output "AZURE_KEY_VAULT_URI" {
  description = "Key Vault URI (empty if disabled)"
  value       = var.enable_key_vault ? module.keyvault[0].uri : ""
}

output "AZURE_MANAGED_IDENTITY_CLIENT_ID" {
  description = "Backend managed identity client ID"
  value       = azurerm_user_assigned_identity.backend.client_id
}
