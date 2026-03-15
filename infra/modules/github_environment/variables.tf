variable "repository" {
  description = "The GitHub repository name."
  type        = string
}

variable "environment" {
  description = "The GitHub environment name."
  type        = string
}

variable "variables" {
  description = "GitHub Actions environment variables to create."
  type        = map(string)
  default     = {}
}

variable "can_admins_bypass" {
  description = "Whether repository admins can bypass environment protection rules."
  type        = bool
  default     = true
}
