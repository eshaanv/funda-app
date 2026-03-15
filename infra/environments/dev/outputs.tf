output "deployer_service_account_email" {
  description = "The GitHub deployer service account email."
  value       = module.gcp.deployer_service_account_email
}

output "workload_identity_provider_name" {
  description = "The Workload Identity provider resource name used by GitHub Actions."
  value       = module.gcp.workload_identity_provider_name
}
