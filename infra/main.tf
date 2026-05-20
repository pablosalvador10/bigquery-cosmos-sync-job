terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.subscription_id
}

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

# ---------------------------------------------------------------------------
# Naming — deterministic suffix for globally unique resources
# ---------------------------------------------------------------------------

locals {
  suffix = substr(sha256("${var.environment_name}-${data.azurerm_subscription.current.subscription_id}"), 0, 6)

  names = {
    log    = "log-${var.environment_name}"
    appi   = "appi-${var.environment_name}"
    acr    = "acr${replace(var.environment_name, "-", "")}${local.suffix}"
    cae    = "cae-${var.environment_name}"
    cosmos = "cosmos-${var.environment_name}-${local.suffix}"
    kv     = "kv-${substr(var.environment_name, 0, 14)}-${local.suffix}"
    mi     = "id-${var.environment_name}-sync"
    job    = "caj-${var.environment_name}-sync"
    ag     = "ag-${var.environment_name}-sync"
    vnet   = "vnet-${var.environment_name}"
    boot   = "caj-${var.environment_name}-bootstrap-secret"
  }

  # Vnet sized for one CAE Consumption subnet (/23 minimum) plus a /24 for PEs.
  network = {
    vnet_cidr = "10.20.0.0/16"
    cae_cidr  = "10.20.0.0/23"
    pe_cidr   = "10.20.2.0/24"
  }

  tags = merge({
    environment = var.environment_name
    managed_by  = "terraform"
    workload    = "bigquery-cosmos-sync"
  }, var.tags)

  job_tags = merge(local.tags, {
    "azd-service-name" = "sync"
  })

  # Cosmos containers — pipeline data + sync metadata.
  # autoscale_max_throughput is only honored when var.cosmos_capacity_mode = "autoscale".
  # Floor billed at max/10. Sized for ~5 GB/day; raise the writes (learners,
  # recommendations) first if data volume grows.
  cosmos_containers = [
    { name = "learners", partition_key_path = "/country", autoscale_max_throughput = 4000 },
    { name = "courses", partition_key_path = "/category", autoscale_max_throughput = 2000 },
    { name = "recommendations", partition_key_path = "/learnerId", autoscale_max_throughput = 4000 },
    { name = "sync_metadata", partition_key_path = "/pipelineName", autoscale_max_throughput = 1000 },
  ]
}

# ---------------------------------------------------------------------------
# Resource Group (existing — must be pre-created)
# ---------------------------------------------------------------------------

data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

# ---------------------------------------------------------------------------
# Managed Identity for the sync job
# ---------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "sync" {
  name                = local.names.mi
  location            = data.azurerm_resource_group.this.location
  resource_group_name = data.azurerm_resource_group.this.name
  tags                = local.tags
}

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

module "logs" {
  source              = "./modules/log-analytics"
  name                = local.names.log
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  tags                = local.tags
}

module "appinsights" {
  source              = "./modules/application-insights"
  name                = local.names.appi
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  workspace_id        = module.logs.id
  tags                = local.tags
}

# ---------------------------------------------------------------------------
# Container Registry
# ---------------------------------------------------------------------------

module "acr" {
  source                        = "./modules/container-registry"
  name                          = local.names.acr
  resource_group_name           = data.azurerm_resource_group.this.name
  location                      = data.azurerm_resource_group.this.location
  sku                           = var.acr_sku
  admin_enabled                 = false
  public_network_access_enabled = var.acr_public_network_access_enabled
  tags                          = local.tags

  pull_identity_principal_ids = [
    azurerm_user_assigned_identity.sync.principal_id,
  ]
}

# ---------------------------------------------------------------------------
# Virtual Network — vnet-integrated Container Apps + private endpoints
#
# Production-grade deployments should never expose Cosmos DB or Key Vault on
# their public endpoints. This sample bakes in the secure-by-default layout:
# Cosmos and Key Vault are reached only through Private Endpoints, the
# Container Apps Environment is vnet-integrated into snet-cae, and outbound
# traffic to BigQuery / GCS exits through a NAT Gateway with a deterministic
# public IP that the BigQuery side can put on its allow-list (or inside a
# VPC Service Controls perimeter). See docs/networking.md for the full picture.
# ---------------------------------------------------------------------------

resource "azurerm_virtual_network" "this" {
  name                = local.names.vnet
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  address_space       = [local.network.vnet_cidr]
  tags                = local.tags
}

resource "azurerm_subnet" "cae" {
  name                 = "snet-cae"
  resource_group_name  = data.azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [local.network.cae_cidr]

  delegation {
    name = "containerapps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "pe" {
  name                              = "snet-pe"
  resource_group_name               = data.azurerm_resource_group.this.name
  virtual_network_name              = azurerm_virtual_network.this.name
  address_prefixes                  = [local.network.pe_cidr]
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = data.azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone" "kv" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = data.azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone" "acr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = data.azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  name                  = "link-cosmos"
  resource_group_name   = data.azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = azurerm_virtual_network.this.id
  tags                  = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "kv" {
  name                  = "link-kv"
  resource_group_name   = data.azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.kv.name
  virtual_network_id    = azurerm_virtual_network.this.id
  tags                  = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "acr" {
  name                  = "link-acr"
  resource_group_name   = data.azurerm_resource_group.this.name
  private_dns_zone_name = azurerm_private_dns_zone.acr.name
  virtual_network_id    = azurerm_virtual_network.this.id
  tags                  = local.tags
}

# ---------------------------------------------------------------------------
# NAT Gateway — deterministic egress for BigQuery / GCS
#
# Without a NAT Gateway, outbound calls from the CAE leave through whatever
# ephemeral SNAT IP Azure picks, which makes it impossible to allow-list the
# pipeline on the GCP side (VPC Service Controls perimeter, BigQuery network
# allow-list, etc.). With a NAT Gateway, every outbound call uses a stable
# public IP that the BigQuery owner can pin. The egress IP is published as
# the `nat_gateway_egress_ip` output. See docs/networking.md.
# ---------------------------------------------------------------------------

resource "azurerm_public_ip" "nat" {
  name                = "pip-nat-${var.environment_name}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  tags                = local.tags
}

resource "azurerm_nat_gateway" "this" {
  name                    = "natgw-${var.environment_name}"
  resource_group_name     = data.azurerm_resource_group.this.name
  location                = data.azurerm_resource_group.this.location
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
  tags                    = local.tags
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  nat_gateway_id       = azurerm_nat_gateway.this.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "cae" {
  subnet_id      = azurerm_subnet.cae.id
  nat_gateway_id = azurerm_nat_gateway.this.id
}

# ---------------------------------------------------------------------------
# Network Security Groups
#
# snet-cae: deny-by-default outbound, with explicit allows for the Azure
# control plane (AzureCloud:443) and for HTTPS to the public Internet (the
# BigQuery API endpoint, which exits through the NAT Gateway above so the
# source IP is stable). Container Apps platform requirements (MCR, AAD,
# AzureMonitor, ACR, App Insights) are all reachable inside AzureCloud.
#
# snet-pe: only intra-VNet inbound on 443; Private Endpoint NICs accept
# nothing else. PE health probes from Azure Load Balancer are exempt.
# ---------------------------------------------------------------------------

resource "azurerm_network_security_group" "cae" {
  name                = "nsg-cae-${var.environment_name}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  tags                = local.tags

  security_rule {
    name                       = "AllowHttpsOutboundAzure"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "AzureCloud"
  }

  security_rule {
    name                       = "AllowHttpsOutboundInternet"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  security_rule {
    name                       = "AllowVnetOutbound"
    priority                   = 120
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "DenyAllOutbound"
    priority                   = 4096
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "cae" {
  subnet_id                 = azurerm_subnet.cae.id
  network_security_group_id = azurerm_network_security_group.cae.id
}

resource "azurerm_network_security_group" "pe" {
  name                = "nsg-pe-${var.environment_name}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  tags                = local.tags

  security_rule {
    name                       = "AllowHttpsFromVnet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "pe" {
  subnet_id                 = azurerm_subnet.pe.id
  network_security_group_id = azurerm_network_security_group.pe.id
}

# ---------------------------------------------------------------------------
# Container Apps Environment
# ---------------------------------------------------------------------------

module "cae" {
  source                     = "./modules/container-apps-environment"
  name                       = local.names.cae
  resource_group_name        = data.azurerm_resource_group.this.name
  location                   = data.azurerm_resource_group.this.location
  log_analytics_workspace_id = module.logs.id
  infrastructure_subnet_id   = azurerm_subnet.cae.id
  tags                       = local.tags
}

# ---------------------------------------------------------------------------
# Cosmos DB — serving database for the sync target
# ---------------------------------------------------------------------------

module "cosmos" {
  source = "./modules/cosmos-db"

  name                          = local.names.cosmos
  resource_group_name           = data.azurerm_resource_group.this.name
  location                      = var.cosmos_location
  database_name                 = var.cosmos_database
  capacity_mode                 = var.cosmos_capacity_mode
  public_network_access_enabled = false
  local_authentication_disabled = true
  zone_redundant                = var.cosmos_zone_redundant
  backup_type                   = var.cosmos_backup_type
  continuous_backup_tier        = var.cosmos_continuous_backup_tier
  log_analytics_workspace_id    = module.logs.id
  tags                          = local.tags

  containers = local.cosmos_containers

  role_assignment_principal_ids = [
    azurerm_user_assigned_identity.sync.principal_id,
    data.azurerm_client_config.current.object_id, # developer access for notebooks
  ]
}

resource "azurerm_private_endpoint" "cosmos" {
  name                = "pe-${local.names.cosmos}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  subnet_id           = azurerm_subnet.pe.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-cosmos"
    private_connection_resource_id = module.cosmos.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.cosmos]
}

# ---------------------------------------------------------------------------
# Key Vault — holds the GCP service account JSON
# ---------------------------------------------------------------------------

module "keyvault" {
  source = "./modules/key-vault"

  name                          = local.names.kv
  resource_group_name           = data.azurerm_resource_group.this.name
  location                      = data.azurerm_resource_group.this.location
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  public_network_access_enabled = false
  tags                          = local.tags

  admin_principal_ids = [data.azurerm_client_config.current.object_id]
  # MI gets Officer (read + write) so the bootstrap job can upload the GCP SA
  # JSON and the sync job can read it via the Container App secret reference.
  secrets_officer_principal_ids = [azurerm_user_assigned_identity.sync.principal_id]
}

resource "azurerm_private_endpoint" "kv" {
  name                = "pe-${local.names.kv}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  subnet_id           = azurerm_subnet.pe.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-kv"
    private_connection_resource_id = module.keyvault.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "kv-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.kv.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.kv]
}

resource "azurerm_private_endpoint" "acr" {
  name                = "pe-${local.names.acr}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  subnet_id           = azurerm_subnet.pe.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-acr"
    private_connection_resource_id = module.acr.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "acr-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.acr.id]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.acr]
}

# ---------------------------------------------------------------------------
# Secret bootstrap — one-shot Container App Job that uploads the GCP service
# account JSON to Key Vault from inside the vnet.
#
# Key Vault is private (no public network access), so we can't `az keyvault
# secret set` from a developer laptop. This job runs inside the vnet-integrated
# CAE, authenticates with the MI, and writes the secret. Triggered once after
# every change to the SA JSON (tracked via filesha256) by null_resource below.
# ---------------------------------------------------------------------------

resource "azurerm_container_app_job" "secret_bootstrap" {
  name                         = local.names.boot
  location                     = data.azurerm_resource_group.this.location
  resource_group_name          = data.azurerm_resource_group.this.name
  container_app_environment_id = module.cae.id
  tags                         = local.tags

  replica_timeout_in_seconds = 300
  replica_retry_limit        = 1

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.sync.id]
  }

  secret {
    name  = "sa-json"
    value = file(var.gcp_sa_json_path)
  }

  template {
    container {
      name    = "bootstrap"
      image   = "mcr.microsoft.com/azure-cli:latest"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args = [
        join(" && ", [
          "set -e",
          "az login --identity --client-id \"$MI_CLIENT_ID\" >/dev/null",
          "printf '%s' \"$SA_JSON\" > /tmp/sa.json",
          "az keyvault secret set --vault-name \"$KV_NAME\" --name \"$SECRET_NAME\" --file /tmp/sa.json --query name -o tsv",
          "rm -f /tmp/sa.json",
          "echo 'bootstrap: secret uploaded'",
        ])
      ]

      env {
        name  = "MI_CLIENT_ID"
        value = azurerm_user_assigned_identity.sync.client_id
      }
      env {
        name  = "KV_NAME"
        value = module.keyvault.name
      }
      env {
        name  = "SECRET_NAME"
        value = var.gcp_sa_secret_name
      }
      env {
        name        = "SA_JSON"
        secret_name = "sa-json"
      }
    }
  }

  depends_on = [
    azurerm_private_endpoint.kv,
    azurerm_private_dns_zone_virtual_network_link.kv,
    module.keyvault,
  ]
}

resource "null_resource" "run_bootstrap" {
  triggers = {
    sa_json_sha = filesha256(var.gcp_sa_json_path)
    job_id      = azurerm_container_app_job.secret_bootstrap.id
    kv_name     = module.keyvault.name
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      JOB="${azurerm_container_app_job.secret_bootstrap.name}"
      RG="${data.azurerm_resource_group.this.name}"
      SUB="${var.subscription_id}"
      echo "[bootstrap] starting $JOB..."
      EXEC=$(az containerapp job start --name "$JOB" --resource-group "$RG" --subscription "$SUB" --query name -o tsv)
      echo "[bootstrap] execution: $EXEC"
      for i in $(seq 1 30); do
        STATUS=$(az containerapp job execution show --name "$JOB" --resource-group "$RG" --subscription "$SUB" --job-execution-name "$EXEC" --query properties.status -o tsv 2>/dev/null || echo "Pending")
        echo "[bootstrap] [$i/30] status=$STATUS"
        case "$STATUS" in
          Succeeded) echo "[bootstrap] secret uploaded."; exit 0 ;;
          Failed)    echo "[bootstrap] FAILED \u2014 check 'az containerapp job execution show -n $JOB -g $RG --job-execution-name $EXEC'"; exit 1 ;;
        esac
        sleep 10
      done
      echo "[bootstrap] timed out"
      exit 1
    EOT
  }
}

# ---------------------------------------------------------------------------
# Container App Job — scheduled BigQuery → Cosmos sync
# ---------------------------------------------------------------------------

module "sync_job" {
  source = "./modules/container-app-job"

  name                = local.names.job
  resource_group_name = data.azurerm_resource_group.this.name
  location            = data.azurerm_resource_group.this.location
  environment_id      = module.cae.id
  image               = var.sync_image
  tags                = local.job_tags

  identity_ids      = [azurerm_user_assigned_identity.sync.id]
  registry_server   = module.acr.login_server
  registry_identity = azurerm_user_assigned_identity.sync.id

  cron_expression          = var.sync_cron_expression
  replica_timeout_seconds  = var.sync_replica_timeout_seconds
  replica_retry_limit      = var.sync_replica_retry_limit
  parallelism              = 1
  replica_completion_count = 1

  cpu    = var.sync_cpu
  memory = var.sync_memory

  env_vars = [
    { name = "AZURE_CLIENT_ID", value = azurerm_user_assigned_identity.sync.client_id },
    { name = "APPLICATIONINSIGHTS_CONNECTION_STRING", value = module.appinsights.connection_string },
    { name = "OTEL_SERVICE_NAME", value = "bq-cosmos-sync" },
    { name = "COSMOS_ENDPOINT", value = module.cosmos.endpoint },
    { name = "COSMOS_DATABASE", value = module.cosmos.database_name },
    { name = "BQ_PROJECT_ID", value = var.bq_project_id },
    { name = "BQ_DATASET", value = var.bq_dataset },
    { name = "BQ_LOCATION", value = var.bq_location },
    { name = "GOOGLE_APPLICATION_CREDENTIALS", value = "/secrets/gcp-sa-json" },
    { name = "SYNC_PIPELINES", value = join(",", var.sync_pipelines) },
    { name = "LOG_LEVEL", value = var.log_level },
  ]

  # GCP service account JSON is sourced from Key Vault and mounted as a secret volume.
  # The Container App secret name (gcp-sa-json) becomes the file name under /secrets/.
  key_vault_secret_uri = "${module.keyvault.uri}secrets/${var.gcp_sa_secret_name}"

  # Wait until the bootstrap job has populated the KV secret — otherwise the
  # Container Apps platform fails to resolve the KV reference at job creation.
  depends_on = [
    null_resource.run_bootstrap,
    azurerm_private_endpoint.cosmos,
  ]
}

# ---------------------------------------------------------------------------
# Alerting — Action Group + four alert rules
# ---------------------------------------------------------------------------

module "action_group" {
  source = "./modules/action-group"

  name                = local.names.ag
  resource_group_name = data.azurerm_resource_group.this.name
  short_name          = "syncalerts"
  email_receivers     = var.alert_email_receivers
  tags                = local.tags
}

module "alerts" {
  source = "./modules/monitor-alerts"

  resource_group_name        = data.azurerm_resource_group.this.name
  location                   = data.azurerm_resource_group.this.location
  job_name                   = module.sync_job.name
  job_resource_id            = module.sync_job.id
  cosmos_account_id          = module.cosmos.id
  log_analytics_workspace_id = module.logs.id
  action_group_id            = module.action_group.id
  tags                       = local.tags

  expected_min_rows         = var.alert_expected_min_rows
  expected_max_rows         = var.alert_expected_max_rows
  cosmos_throttle_threshold = var.alert_cosmos_throttle_threshold
}
