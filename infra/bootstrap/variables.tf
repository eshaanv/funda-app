variable "project_id" {
  description = "The GCP project that will hold the Terraform state bucket."
  type        = string
}

variable "region" {
  description = "The default region used by the Google provider."
  type        = string
}

variable "bucket_name" {
  description = "The globally unique GCS bucket name for Terraform state."
  type        = string
}

variable "bucket_location" {
  description = "The multi-region or region for the Terraform state bucket."
  type        = string
  default     = "US"
}

variable "labels" {
  description = "Labels applied to the Terraform state bucket."
  type        = map(string)
  default     = {}
}

variable "state_bucket_object_admin_members" {
  description = "IAM members that need Storage Object Admin on the Terraform state bucket."
  type        = list(string)
  default     = []
}

variable "service_usage_viewer_members" {
  description = "IAM members that need Service Usage viewer access."
  type        = list(string)
  default     = []
}
