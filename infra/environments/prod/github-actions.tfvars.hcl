project_id                    = "funda-prod-490316"
project_number                = "333824692455"
region                        = "us-central1"
artifact_registry_repository  = "funda-app"
cloud_run_service_name        = "funda-app"
runtime_service_account_email = "333824692455-compute@developer.gserviceaccount.com"
terraform_state_bucket        = "funda-prod-490316-funda-app-tfstate"
terraform_state_prefix        = "funda-app/prod"
github_environment_name       = "production"

labels = {
  app         = "funda-app"
  environment = "production"
  managed_by  = "terraform"
}
