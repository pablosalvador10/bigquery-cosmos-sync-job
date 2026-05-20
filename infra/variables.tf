variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "environment_name" {
  description = "Environment name used in all resource names (e.g. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

# --- Feature flags ---

variable "enable_cosmos_db" {
  description = "Provision Cosmos DB resources"
  type        = bool
  default     = true
}

variable "enable_key_vault" {
  description = "Provision Key Vault"
  type        = bool
  default     = false
}

# --- Container images ---

variable "backend_image" {
  description = "Backend container image"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

variable "frontend_image" {
  description = "Frontend container image"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

# --- Backend sizing ---

variable "backend_cpu" {
  description = "Backend CPU allocation"
  type        = number
  default     = 0.5
}

variable "backend_memory" {
  description = "Backend memory allocation"
  type        = string
  default     = "1Gi"
}
