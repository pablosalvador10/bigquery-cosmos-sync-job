# --- Variables ---
variable "name" {
  description = "Container App Job name"
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

variable "environment_id" {
  description = "Container Apps Environment ID"
  type        = string
}

variable "image" {
  description = "Container image (FQ tag)"
  type        = string
}

variable "cpu" {
  description = "CPU cores"
  type        = number
  default     = 1.0
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "2Gi"
}

variable "cron_expression" {
  description = "Cron schedule in UTC (5-field POSIX format)"
  type        = string
  default     = "0 2 * * *"
}

variable "replica_timeout_seconds" {
  description = "Max seconds a replica can run before being killed"
  type        = number
  default     = 1800
}

variable "replica_retry_limit" {
  description = "Platform-level retries on non-zero exit"
  type        = number
  default     = 2
}

variable "parallelism" {
  description = "Number of replicas to run in parallel per execution"
  type        = number
  default     = 1
}

variable "replica_completion_count" {
  description = "Number of successful replicas required for the execution to succeed"
  type        = number
  default     = 1
}

variable "env_vars" {
  description = "Environment variables"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "identity_ids" {
  description = "User-assigned managed identity IDs"
  type        = list(string)
  default     = []
}

variable "registry_server" {
  description = "Container registry login server"
  type        = string
  default     = ""
}

variable "registry_identity" {
  description = "Managed identity resource ID for registry pull"
  type        = string
  default     = ""
}

variable "key_vault_secret_uri" {
  description = "Full Key Vault secret URI for the GCP SA JSON (empty disables secret mount)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# --- Locals ---
locals {
  has_kv_secret    = var.key_vault_secret_uri != ""
  has_registry     = var.registry_server != ""
  has_identity     = length(var.identity_ids) > 0
  primary_identity = local.has_identity ? var.identity_ids[0] : ""
}

# --- Resource ---
resource "azurerm_container_app_job" "this" {
  name                         = var.name
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.environment_id
  tags                         = var.tags

  replica_timeout_in_seconds = var.replica_timeout_seconds
  replica_retry_limit        = var.replica_retry_limit

  schedule_trigger_config {
    cron_expression          = var.cron_expression
    parallelism              = var.parallelism
    replica_completion_count = var.replica_completion_count
  }

  dynamic "identity" {
    for_each = local.has_identity ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = var.identity_ids
    }
  }

  dynamic "registry" {
    for_each = local.has_registry ? [1] : []
    content {
      server   = var.registry_server
      identity = var.registry_identity
    }
  }

  dynamic "secret" {
    for_each = local.has_kv_secret ? [1] : []
    content {
      name                = "gcp-sa-json"
      key_vault_secret_id = var.key_vault_secret_uri
      identity            = local.primary_identity
    }
  }

  template {
    container {
      name   = "sync"
      image  = var.image
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      dynamic "volume_mounts" {
        for_each = local.has_kv_secret ? [1] : []
        content {
          name = "gcp-creds"
          path = "/secrets"
        }
      }
    }

    dynamic "volume" {
      for_each = local.has_kv_secret ? [1] : []
      content {
        name         = "gcp-creds"
        storage_type = "Secret"
      }
    }
  }
}

# --- Outputs ---
output "id" {
  value = azurerm_container_app_job.this.id
}

output "name" {
  value = azurerm_container_app_job.this.name
}
