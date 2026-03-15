output "environment" {
  description = "The GitHub environment name."
  value       = github_repository_environment.this.environment
}
