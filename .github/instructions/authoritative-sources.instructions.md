---
description: "Authoritative sources and reference tools for Azure, Terraform, and documentation lookups. Use when unsure about Azure service configuration, Terraform resource syntax, best practices, or needing official documentation."
---

# Authoritative Sources & Reference Tools

## When In Doubt — Where to Look

This instruction tells the agent which sources to consult for accurate, up-to-date information. **Always prefer these over training data which may be outdated.**

## MCP Tools Available to the Agent

The agent has access to Azure MCP tools that provide real-time, accurate Azure information. **Use these FIRST before guessing.**

### Azure Documentation & Best Practices
| MCP Tool | When to Use |
|----------|-------------|
| `mcp_azure_mcp_documentation` | Look up official Azure documentation for any service |
| `mcp_azure_mcp_get_bestpractices` | Get best practices for Azure development and deployment |
| `mcp_azure_mcp_appservice` | Azure App Service configuration and patterns |
| `mcp_azure_mcp_cosmos` | Cosmos DB configuration, queries, and optimization |
| `mcp_azure_mcp_monitor` | Azure Monitor, metrics, and alerting patterns |
| `mcp_azure_mcp_applicationinsights` | Application Insights setup and query patterns |
| `mcp_azure_mcp_keyvault` | Key Vault secrets, keys, and certificate management |
| `mcp_azure_mcp_storage` | Azure Storage (Blob, Queue, Table) patterns |
| `mcp_azure_mcp_eventgrid` | Event Grid topics and subscriptions |
| `mcp_azure_mcp_servicebus` | Service Bus queues, topics, and messaging |
| `mcp_azure_mcp_redis` | Azure Redis Cache configuration |
| `mcp_azure_mcp_postgres` | Azure Database for PostgreSQL |
| `mcp_azure_mcp_sql` | Azure SQL Database |
| `mcp_azure_mcp_search` | Azure AI Search (formerly Cognitive Search) |
| `mcp_azure_mcp_foundry` | Azure AI Foundry project management |

### Infrastructure as Code
| MCP Tool | When to Use |
|----------|-------------|
| `mcp_azure_mcp_deploy` | Deployment patterns and azd workflows |
| `mcp_azure_mcp_azd` | Azure Developer CLI commands and configuration |
| `mcp_azure_mcp_azureterraformbestpractices` | Terraform best practices for Azure |
| `mcp_bicep_get_bicep_best_practices` | Bicep IaC best practices |
| `mcp_bicep_get_az_resource_type_schema` | Azure resource type schemas |

### Monitoring & Observability
| MCP Tool | When to Use |
|----------|-------------|
| `mcp_azure_mcp_monitor` | Azure Monitor configuration |
| `mcp_azure_mcp_applicationinsights` | App Insights setup and KQL queries |
| `mcp_azure_mcp_grafana` | Grafana dashboard integration |

### Security & Identity
| MCP Tool | When to Use |
|----------|-------------|
| `mcp_azure_mcp_keyvault` | Secret and key management |
| `mcp_azure_mcp_role` | RBAC role assignments and permissions |

## Decision: When to Use MCP vs. Local Knowledge

| Scenario | Action |
|----------|--------|
| **Azure resource configuration** | Use `mcp_azure_mcp_documentation` or service-specific MCP tool |
| **Terraform resource syntax** | Use `mcp_azure_mcp_azureterraformbestpractices` + check `infra/modules/core/main.tf` for existing patterns |
| **Best practices for Azure service** | Use `mcp_azure_mcp_get_bestpractices` with the service name |
| **How this template does things** | Check `.github/skills/` and `.github/instructions/` FIRST |
| **Python/FastAPI patterns** | Check `.github/instructions/backend.instructions.md` and `py_fastapi.instructions.md` |
| **React/TypeScript patterns** | Check `.github/instructions/frontend.instructions.md` |
| **Unknown Azure service** | Use `mcp_azure_mcp_documentation` to research before implementing |

## Precedence Order

When resolving how to do something:

1. **This repo's instructions/skills** — always check first for template-specific conventions
2. **This repo's existing code** — follow established patterns in `py/apps/`, `py/libs/`, `infra/`
3. **MCP Azure tools** — for Azure-specific configuration, syntax, and best practices
4. **Official documentation** — Azure docs, Terraform registry, Python/TypeScript docs
5. **Training knowledge** — last resort, may be outdated

## Common Lookup Patterns

### "How do I configure Azure service X?"
1. Check if `.github/instructions/azure-services.instructions.md` covers it
2. If not, use `mcp_azure_mcp_documentation` with the service name
3. Use `mcp_azure_mcp_get_bestpractices` for architecture guidance
4. Follow `add-azure-resource` skill for Terraform provisioning

### "What's the Terraform syntax for resource Y?"
1. Check `infra/modules/core/main.tf` for existing patterns
2. Use `mcp_azure_mcp_azureterraformbestpractices` for Azure-specific Terraform
3. Follow `add-azure-resource` skill for the workflow

### "How do I set up monitoring/tracing?"
1. Follow `observability-setup` skill
2. Check `core/telemetry.py` for existing OTel setup
3. Use `mcp_azure_mcp_applicationinsights` for App Insights specifics

### "How do I handle secrets/credentials?"
1. Check `security-and-config.instructions.md`
2. Check `FoundrySettings` pattern in `py/libs/foundrykit/foundrykit/config.py`
3. Use `mcp_azure_mcp_keyvault` for Key Vault integration
