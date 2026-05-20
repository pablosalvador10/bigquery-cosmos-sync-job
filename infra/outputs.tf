output "AZURE_RESOURCE_GROUP_NAME" {
  description = "Resource group name"
  value       = data.azurerm_resource_group.this.name
}

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  description = "ACR login server (used by azd for image push)"
  value       = module.acr.login_server
}

output "AZURE_COSMOS_ENDPOINT" {
  description = "Cosmos DB endpoint"
  value       = module.cosmos.endpoint
}

output "AZURE_COSMOS_DATABASE" {
  description = "Cosmos DB SQL database name"
  value       = module.cosmos.database_name
}

output "AZURE_KEY_VAULT_URI" {
  description = "Key Vault URI"
  value       = module.keyvault.uri
}

output "AZURE_KEY_VAULT_NAME" {
  description = "Key Vault name (use with `az keyvault secret set`)"
  value       = module.keyvault.name
}

output "AZURE_MANAGED_IDENTITY_CLIENT_ID" {
  description = "Sync job managed identity client ID"
  value       = azurerm_user_assigned_identity.sync.client_id
}

output "AZURE_APPINSIGHTS_CONNECTION_STRING" {
  description = "Application Insights connection string"
  value       = module.appinsights.connection_string
  sensitive   = true
}

output "AZURE_LOG_ANALYTICS_WORKSPACE_ID" {
  description = "Log Analytics workspace ID (for KQL queries)"
  value       = module.logs.workspace_id
}

output "SYNC_JOB_NAME" {
  description = "Container App Job name (use with `az containerapp job start`)"
  value       = module.sync_job.name
}

output "SYNC_JOB_RESOURCE_ID" {
  description = "Container App Job ARM resource ID"
  value       = module.sync_job.id
}

output "NAT_GATEWAY_EGRESS_IP" {
  description = <<-EOT
    Deterministic public IP used for all outbound traffic from the sync job
    (BigQuery API calls in particular). Hand this to the BigQuery side to
    add to their VPC Service Controls perimeter or any IP allow-list.
  EOT
  value       = azurerm_public_ip.nat.ip_address
}
