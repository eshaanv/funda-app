variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "project_number" {
  description = "The numeric GCP project number."
  type        = string
}

variable "region" {
  description = "The Cloud Run and Artifact Registry region."
  type        = string
}

variable "artifact_registry_repository" {
  description = "The Artifact Registry repository used for deploy images."
  type        = string
}

variable "cloud_run_service_name" {
  description = "The Cloud Run service name."
  type        = string
}

variable "runtime_service_account_email" {
  description = "The runtime service account attached to Cloud Run."
  type        = string
}

variable "terraform_state_bucket" {
  description = "The GCS bucket used for the prod Terraform backend."
  type        = string
}

variable "terraform_state_prefix" {
  description = "The backend prefix used for the prod Terraform state."
  type        = string
}

variable "deployer_service_account_id" {
  description = "The account ID for the GitHub deployer service account."
  type        = string
  default     = "github-deploy"
}

variable "workload_identity_pool_id" {
  description = "The Workload Identity pool ID."
  type        = string
  default     = "github"
}

variable "workload_identity_provider_id" {
  description = "The Workload Identity provider ID."
  type        = string
  default     = "funda-app"
}

variable "github_owner" {
  description = "The GitHub repository owner used by the provider."
  type        = string
  default     = "eshaanv"
}

variable "github_repository" {
  description = "The GitHub repository name."
  type        = string
  default     = "funda-app"
}

variable "github_environment_name" {
  description = "The GitHub environment name managed by this stack."
  type        = string
  default     = "production"
}

variable "github_environment_extra_vars" {
  description = "Additional GitHub Actions environment variables."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Labels applied to supported GCP resources."
  type        = map(string)
  default     = {}
}
