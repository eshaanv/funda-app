variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "project_number" {
  description = "The numeric GCP project number."
  type        = string
}

variable "region" {
  description = "The region for Artifact Registry."
  type        = string
}

variable "repository_id" {
  description = "The Artifact Registry repository ID."
  type        = string
}

variable "repository_description" {
  description = "Description for the Artifact Registry repository."
  type        = string
  default     = "Docker images for Funda"
}

variable "deployer_service_account_id" {
  description = "The account ID for the GitHub deployer service account."
  type        = string
}

variable "runtime_service_account_email" {
  description = "The runtime service account attached to Cloud Run."
  type        = string
}

variable "workload_identity_pool_id" {
  description = "The Workload Identity pool ID."
  type        = string
}

variable "workload_identity_pool_display_name" {
  description = "Display name for the Workload Identity pool."
  type        = string
  default     = "GitHub Actions pool"
}

variable "workload_identity_provider_id" {
  description = "The Workload Identity provider ID."
  type        = string
}

variable "workload_identity_provider_display_name" {
  description = "Display name for the Workload Identity provider."
  type        = string
  default     = "GitHub provider for funda-app"
}

variable "github_repository_owner" {
  description = "The GitHub repository owner."
  type        = string
}

variable "github_repository_name" {
  description = "The GitHub repository name."
  type        = string
}

variable "enabled_services" {
  description = "Project services required by the deploy infrastructure."
  type        = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "sts.googleapis.com",
  ]
}

variable "labels" {
  description = "Labels applied to supported resources."
  type        = map(string)
  default     = {}
}
