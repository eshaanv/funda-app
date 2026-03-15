locals {
  github_environment_vars = merge(
    var.github_environment_extra_vars,
    {
      GOOGLE_CLOUD_PROJECT           = var.project_id
      CLOUD_RUN_LOCATION             = var.region
      ARTIFACT_REGISTRY_REPOSITORY   = var.artifact_registry_repository
      CLOUD_RUN_SERVICE_NAME         = var.cloud_run_service_name
      GCP_SERVICE_ACCOUNT_EMAIL      = module.gcp.deployer_service_account_email
      GCP_WORKLOAD_IDENTITY_PROVIDER = module.gcp.workload_identity_provider_name
      TERRAFORM_STATE_BUCKET         = var.terraform_state_bucket
      TERRAFORM_STATE_PREFIX         = var.terraform_state_prefix
    },
  )
}

module "gcp" {
  source = "../../modules/project_deploy_infra"

  project_id                              = var.project_id
  project_number                          = var.project_number
  region                                  = var.region
  repository_id                           = var.artifact_registry_repository
  deployer_service_account_id             = var.deployer_service_account_id
  runtime_service_account_email           = var.runtime_service_account_email
  workload_identity_pool_id               = var.workload_identity_pool_id
  workload_identity_provider_id           = var.workload_identity_provider_id
  github_repository_owner                 = var.github_owner
  github_repository_name                  = var.github_repository
  workload_identity_provider_display_name = "GitHub provider for ${var.github_repository}"
  labels                                  = var.labels
}

module "github_environment" {
  source = "../../modules/github_environment"

  repository  = var.github_repository
  environment = var.github_environment_name
  variables   = local.github_environment_vars
}
