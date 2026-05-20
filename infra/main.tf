terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

# ---------------------------------------------------------------------------
# Naming — deterministic hash suffix for globally unique resources
# ---------------------------------------------------------------------------

locals {
  suffix = substr(sha256("${var.environment_name}-${data.azurerm_subscription.current.subscription_id}"), 0, 6)

  names = {
    rg       = "${var.environment_name}-rg"
    log      = "log-${var.environment_name}"
    appi     = "appi-${var.environment_name}"
    acr      = "acr${replace(var.environment_name, "-", "")}${local.suffix}"
    cae      = "cae-${var.environment_name}"
    cosmos   = "cosmos-${var.environment_name}-${local.suffix}"
    kv       = "kv-${substr(var.environment_name, 0, 14)}-${local.suffix}"
    mi       = "id-${var.environment_name}-backend"
    backend  = "ca-backend-${var.environment_name}"
    frontend = "ca-frontend-${var.environment_name}"
  }

  tags = {
    environment = var.environment_name
    managed_by  = "terraform"
    template    = "agentic-ai-apps-azure"
  }
}

# ---------------------------------------------------------------------------
# Resource Group
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "this" {
  name     = local.names.rg
  location = var.location
  tags     = local.tags
}

# ---------------------------------------------------------------------------
# Managed Identity (used by backend Container App for all Azure access)
# ---------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "backend" {
  name                = local.names.mi
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

module "logs" {
  source              = "./modules/log-analytics"
  name                = local.names.log
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags
}

module "appinsights" {
  source              = "./modules/application-insights"
  name                = local.names.appi
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  workspace_id        = module.logs.id
  tags                = local.tags
}

# ---------------------------------------------------------------------------
# Container Registry
# ---------------------------------------------------------------------------

module "acr" {
  source              = "./modules/container-registry"
  name                = local.names.acr
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags

  pull_identity_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ---------------------------------------------------------------------------
# Container Apps Environment
# ---------------------------------------------------------------------------

module "cae" {
  source                     = "./modules/container-apps-environment"
  name                       = local.names.cae
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = module.logs.id
  tags                       = local.tags
}

# ---------------------------------------------------------------------------
# Cosmos DB (conditional)
# ---------------------------------------------------------------------------

module "cosmos" {
  count  = var.enable_cosmos_db ? 1 : 0
  source = "./modules/cosmos-db"

  name                = local.names.cosmos
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  database_name       = var.environment_name
  tags                = local.tags

  containers = [
    { name = "messages", partition_key_path = "/session_id" },
    { name = "sessions", partition_key_path = "/session_id" },
  ]

  role_assignment_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ---------------------------------------------------------------------------
# Key Vault (conditional)
# ---------------------------------------------------------------------------

module "keyvault" {
  count  = var.enable_key_vault ? 1 : 0
  source = "./modules/key-vault"

  name                = local.names.kv
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  tags                = local.tags

  admin_principal_ids = [data.azurerm_client_config.current.object_id]
  secrets_user_principal_ids = [
    azurerm_user_assigned_identity.backend.principal_id,
  ]
}

# ---------------------------------------------------------------------------
# Backend Container App
# ---------------------------------------------------------------------------

module "backend" {
  source = "./modules/container-app"

  name                = local.names.backend
  resource_group_name = azurerm_resource_group.this.name
  environment_id      = module.cae.id
  image               = var.backend_image
  target_port         = 8001
  cpu                 = var.backend_cpu
  memory              = var.backend_memory
  tags                = local.tags

  identity_ids      = [azurerm_user_assigned_identity.backend.id]
  registry_server   = module.acr.login_server
  registry_identity = azurerm_user_assigned_identity.backend.id

  env_vars = concat(
    [
      { name = "APPLICATIONINSIGHTS_CONNECTION_STRING", value = module.appinsights.connection_string },
      { name = "AZURE_CLIENT_ID", value = azurerm_user_assigned_identity.backend.client_id },
      { name = "FOUNDRY_CREDENTIAL_MODE", value = "managed_identity" },
      { name = "STORAGE_MODE", value = var.enable_cosmos_db ? "cosmos" : "inmemory" },
    ],
    var.enable_cosmos_db ? [
      { name = "COSMOS_ENDPOINT", value = module.cosmos[0].endpoint },
      { name = "COSMOS_DATABASE_NAME", value = module.cosmos[0].database_name },
    ] : [],
  )
}

# ---------------------------------------------------------------------------
# Frontend Container App
# ---------------------------------------------------------------------------

module "frontend" {
  source = "./modules/container-app"

  name                = local.names.frontend
  resource_group_name = azurerm_resource_group.this.name
  environment_id      = module.cae.id
  image               = var.frontend_image
  target_port         = 80
  cpu                 = 0.25
  memory              = "0.5Gi"
  tags                = local.tags

  registry_server   = module.acr.login_server
  registry_identity = azurerm_user_assigned_identity.backend.id
  identity_ids      = [azurerm_user_assigned_identity.backend.id]
}
