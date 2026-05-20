terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

variable "project_id" {
  description = "GCP project hosting the BigQuery dataset"
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure AD tenant ID that issues the managed identity's token"
  type        = string
}

variable "azure_mi_object_id" {
  description = "Object ID (sub claim) of the Azure user-assigned managed identity"
  type        = string
}

variable "bigquery_sa_email" {
  description = "BigQuery service account the Azure workload will impersonate"
  type        = string
}

variable "pool_id" {
  description = "Workload Identity Pool ID"
  type        = string
  default     = "azure-pool"
}

variable "provider_id" {
  description = "Workload Identity Pool OIDC Provider ID"
  type        = string
  default     = "azure-oidc"
}

resource "google_iam_workload_identity_pool" "azure" {
  workload_identity_pool_id = var.pool_id
  display_name              = "Azure workload pool"
  description               = "Federation pool for Azure-side workloads."
}

resource "google_iam_workload_identity_pool_provider" "azure_oidc" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.azure.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  display_name                       = "Azure OIDC"

  oidc {
    issuer_uri        = "https://sts.windows.net/${var.azure_tenant_id}/"
    allowed_audiences = ["api://AzureADTokenExchange"]
  }

  attribute_mapping = {
    "google.subject" = "assertion.sub"
  }
}

# Grant the federated Azure principal the right to impersonate the BigQuery SA.
resource "google_service_account_iam_member" "wif_user" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.bigquery_sa_email}"
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.azure.name}/subject/${var.azure_mi_object_id}"
}

# Emit the external_account JSON config the Python app will mount.
locals {
  external_account = {
    type               = "external_account"
    audience           = "//iam.googleapis.com/${google_iam_workload_identity_pool_provider.azure_oidc.name}"
    subject_token_type = "urn:ietf:params:oauth:token-type:jwt"
    token_url          = "https://sts.googleapis.com/v1/token"
    service_account_impersonation_url = format(
      "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/%s:generateAccessToken",
      var.bigquery_sa_email,
    )
    credential_source = {
      url = format(
        "https://login.microsoftonline.com/%s/oauth2/v2.0/token?api-version=2018-02-01&resource=api://AzureADTokenExchange",
        var.azure_tenant_id,
      )
      headers = {
        Metadata = "True"
      }
      format = {
        type                  = "json"
        subject_token_field_name = "access_token"
      }
    }
  }
}

output "external_account_json" {
  description = "Mount this JSON at /secrets/gcp-sa-json in place of the SA key. Non-secret."
  value       = jsonencode(local.external_account)
}

output "pool_provider_resource_name" {
  description = "Full resource name of the WIF OIDC provider"
  value       = google_iam_workload_identity_pool_provider.azure_oidc.name
}
