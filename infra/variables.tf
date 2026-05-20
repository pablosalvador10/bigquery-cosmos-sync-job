variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "environment_name" {
  description = "Environment name used in all resource names (e.g. dev, staging, prod). Must be lowercase, 2-20 chars."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,19}$", var.environment_name))
    error_message = "environment_name must be lowercase alphanumerics + hyphens, 2-20 chars."
  }
}

variable "resource_group_name" {
  description = "Name of an existing resource group to deploy into. Must already exist."
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Extra tags merged on top of the defaults"
  type        = map(string)
  default     = {}
}

# --- Container Registry ---

variable "acr_sku" {
  description = "ACR SKU. Premium is required for Private Endpoints, customer-managed keys, and trusted-services bypass."
  type        = string
  default     = "Premium"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "acr_sku must be 'Basic', 'Standard', or 'Premium'."
  }
}

variable "acr_public_network_access_enabled" {
  description = <<-EOT
    If true, ACR accepts traffic on its public endpoint as well as via the
    Private Endpoint. Default true so `azd up` works frictionlessly from a
    developer laptop and ACR Tasks (`remoteBuild: true`) can push images.
    Flip to false once your CI pushes images from inside the vnet or via a
    trusted-services exemption. The PE is created either way.
  EOT
  type        = bool
  default     = true
}

# --- Sync job image / sizing ---

variable "sync_image" {
  description = "Container image for the sync job (set by azd after first deploy)"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

variable "sync_cpu" {
  description = "CPU cores for the sync job container"
  type        = number
  default     = 1.0
}

variable "sync_memory" {
  description = "Memory for the sync job container"
  type        = string
  default     = "2Gi"
}

# --- Sync job schedule / retry ---

variable "sync_cron_expression" {
  description = "Cron expression for the daily run (UTC). Default: 02:00 UTC daily."
  type        = string
  default     = "0 2 * * *"
}

variable "sync_replica_timeout_seconds" {
  description = "Max seconds a single job execution can run before being killed"
  type        = number
  default     = 1800
}

variable "sync_replica_retry_limit" {
  description = "Platform-level retries on non-zero exit"
  type        = number
  default     = 2
}

variable "sync_pipelines" {
  description = "Pipelines the job should run (empty list = all registered)"
  type        = list(string)
  default     = ["courses", "learners", "recommendations"]
}

# --- BigQuery ---

variable "bq_project_id" {
  description = "Google Cloud project ID hosting the BigQuery source dataset"
  type        = string
}

variable "bq_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "learnsphere"
}

variable "bq_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "gcp_sa_secret_name" {
  description = "Name of the Key Vault secret containing the GCP service account JSON"
  type        = string
  default     = "gcp-bigquery-sa"
}

variable "gcp_sa_json_path" {
  description = "Path to the GCP service account JSON file, used by the secret-bootstrap job to populate Key Vault. Relative to the infra/ root."
  type        = string
  default     = "../secrets/gcp-sa.json"
}

# --- Cosmos ---

variable "cosmos_location" {
  description = "Azure region for the Cosmos DB account. Can differ from the resource group's region; the private endpoint is region-agnostic."
  type        = string
  default     = "eastus2"
}

variable "cosmos_database" {
  description = "Cosmos DB SQL database name"
  type        = string
  default     = "learnsphere"
}

variable "cosmos_capacity_mode" {
  description = <<-EOT
    How Cosmos containers are billed.

      * "serverless" — pay per RU consumed. No floor. Hard burst cap of
        5,000 RU/s per container. Best for daily batch + low read traffic.
      * "autoscale"  — provisioned autoscale. You pay max/10 RU/s as a
        floor 24/7 in exchange for unlimited burst up to the per-container
        autoscale_max_throughput.

    NOTE: switching this on an existing account requires recreating the
    Cosmos account (Azure does not allow in-place mode changes).
  EOT
  type        = string
  default     = "serverless"

  validation {
    condition     = contains(["serverless", "autoscale"], var.cosmos_capacity_mode)
    error_message = "cosmos_capacity_mode must be 'serverless' or 'autoscale'."
  }
}

variable "cosmos_zone_redundant" {
  description = "If true, the Cosmos primary region is zone-redundant. Recommended for any production deployment."
  type        = bool
  default     = true
}

variable "cosmos_backup_type" {
  description = "Cosmos backup type: 'Continuous' (point-in-time restore, recommended) or 'Periodic'."
  type        = string
  default     = "Continuous"

  validation {
    condition     = contains(["Continuous", "Periodic"], var.cosmos_backup_type)
    error_message = "cosmos_backup_type must be 'Continuous' or 'Periodic'."
  }
}

variable "cosmos_continuous_backup_tier" {
  description = "Continuous-backup retention tier when cosmos_backup_type = 'Continuous'. One of 'Continuous7Days' or 'Continuous30Days'."
  type        = string
  default     = "Continuous7Days"

  validation {
    condition     = contains(["Continuous7Days", "Continuous30Days"], var.cosmos_continuous_backup_tier)
    error_message = "cosmos_continuous_backup_tier must be 'Continuous7Days' or 'Continuous30Days'."
  }
}

# --- Observability / alerts ---

variable "log_level" {
  description = "Python logging level for the sync job"
  type        = string
  default     = "INFO"
}

variable "alert_email_receivers" {
  description = "Email addresses notified by the sync action group"
  type = list(object({
    name  = string
    email = string
  }))
  default = []
}

variable "alert_expected_min_rows" {
  description = "Volume-anomaly alert fires when total rowsRead drops below this"
  type        = number
  default     = 1
}

variable "alert_expected_max_rows" {
  description = "Volume-anomaly alert fires when total rowsRead exceeds this"
  type        = number
  default     = 10000000
}

variable "alert_cosmos_throttle_threshold" {
  description = "Number of Cosmos 429 (throttle) responses in a 15-minute window before alerting. Sustained throttling means it's time to consider autoscale."
  type        = number
  default     = 100
}
