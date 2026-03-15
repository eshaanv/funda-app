output "artifact_registry_repository_id" {
  description = "The Artifact Registry repository ID."
  value       = google_artifact_registry_repository.images.repository_id
}

output "artifact_registry_repository_name" {
  description = "The fully qualified Artifact Registry repository name."
  value       = google_artifact_registry_repository.images.name
}

output "deployer_service_account_email" {
  description = "The GitHub deployer service account email."
  value       = google_service_account.github_deployer.email
}

output "deployer_service_account_name" {
  description = "The fully qualified GitHub deployer service account name."
  value       = google_service_account.github_deployer.name
}

output "github_principal" {
  description = "The GitHub principalSet member allowed to impersonate the deployer service account."
  value       = local.github_principal
}

output "runtime_service_account_email" {
  description = "The runtime service account email attached to Cloud Run."
  value       = var.runtime_service_account_email
}

output "workload_identity_provider_name" {
  description = "The Workload Identity provider resource name used by GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}
