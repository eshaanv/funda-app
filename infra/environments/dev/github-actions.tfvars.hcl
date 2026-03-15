project_id                    = "stai-485819"
project_number                = "223110395358"
region                        = "us-central1"
artifact_registry_repository  = "funda-app"
cloud_run_service_name        = "funda-app"
runtime_service_account_email = "223110395358-compute@developer.gserviceaccount.com"
terraform_state_bucket        = "stai-485819-funda-app-tfstate"
terraform_state_prefix        = "funda-app/dev"
github_environment_name       = "develop"

labels = {
  app         = "funda-app"
  environment = "develop"
  managed_by  = "terraform"
}
