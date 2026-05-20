---
description: Azure service integration patterns. Use when configuring Azure AI Foundry, Cosmos DB, Container Apps, Application Insights, or managed identity.
applyTo: 'py/libs/foundrykit/**'
---

# Azure Services Integration

## Azure AI Foundry
- **Client**: `FoundryClient` in `py/libs/foundrykit/foundrykit/client.py`.
- Singleton: always use `get_foundry_client()` — never create multiple instances.
- Config: `AZURE_FOUNDRY_PROJECT_ENDPOINT` (Foundry service URL), `AZURE_OPENAI_CHAT_MODEL` (default: `gpt-4.1-mini`).
- **AgentManager**: create, run, and stream agents. Use `temporary_agent()` context manager for ephemeral agents (auto-deletes on exit).
- **ToolRegistry**: `@registry.register` wraps functions with OpenTelemetry tracing. Call `registry.build_toolset()` to get SDK-compatible `ToolSet`.

## Azure Cosmos DB
- **SDK**: `azure-cosmos` async client (`CosmosClient` from `azure.cosmos.aio`).
- **Auth**: `DefaultAzureCredential` — no connection strings.
- **Consistency**: Session level (set in Terraform).
- **Partition key**: `/session_id` for messages container — queries within session never cross partitions.
- **Queries**: always parameterized (`@param` syntax) — never interpolate user input.

## Azure Container Apps
- Backend and frontend deployed as separate Container Apps.
- Backend: port 8001, external ingress.
- Frontend: port 80 (nginx), external ingress.
- Use User-Assigned Managed Identity for RBAC to Azure services.
- Environment variables injected via `azure.yaml` wiring from Terraform outputs.

## Azure Service Bus (extension pattern)
- Add as a Terraform resource via `add-azure-resource` skill.
- Use `azure-servicebus` async SDK in a background processor.
- Keep processors in `py/apps/processors/` or as a separate workspace member.
- Auth: `DefaultAzureCredential` — no connection strings.
- Always close clients/receivers in `finally` blocks.

## Azure Key Vault
- Use for secrets that should not be in environment variables.
- Reference via `@Microsoft.KeyVault(...)` in Container Apps env config.
- Add Terraform resource + RBAC role assignment for managed identity.

## Application Insights
- Connection string via `APPLICATIONINSIGHTS_CONNECTION_STRING` env var.
- OTel exporter mode `azure` in `core/telemetry.py` sends traces.
- Provisioned via `infra/modules/application-insights/` module.

## Managed Identity Pattern
- Use User-Assigned Managed Identity for all Azure service access.
- Assign RBAC roles in Terraform (`azurerm_role_assignment`).
- In code: `DefaultAzureCredential()` for dev, `ManagedIdentityCredential(client_id=...)` for prod.
- Config toggle: `FOUNDRY_CREDENTIAL_MODE` (dev | managed_identity).

## Azure Container Apps
- Backend and frontend deployed as separate Container Apps via `infra/modules/container-app/`.
- Container App Environment provisioned via `infra/modules/container-apps-environment/`.
- Environment variables injected from `azure.yaml` bindings and Terraform outputs.
- Health checks at `/healthz` endpoint.
- Use User-Assigned Managed Identity for RBAC to all Azure services.
- OpenTelemetry SDK exports traces, metrics, and logs.
- `OTEL_EXPORTER=azure` activates the Azure Monitor exporter.

## Managed Identity
- Production uses user-assigned managed identity (`AZURE_CLIENT_ID`).
- `FOUNDRY_CREDENTIAL_MODE=managed_identity` activates `ManagedIdentityCredential`.
- RBAC roles assigned in Terraform for Cosmos DB and AI Foundry access.
