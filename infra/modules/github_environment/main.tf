resource "github_repository_environment" "this" {
  repository        = var.repository
  environment       = var.environment
  can_admins_bypass = var.can_admins_bypass
}

resource "github_actions_environment_variable" "vars" {
  for_each = var.variables

  repository    = var.repository
  environment   = github_repository_environment.this.environment
  variable_name = each.key
  value         = each.value
}
