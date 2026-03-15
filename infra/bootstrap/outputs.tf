output "bucket_name" {
  description = "The created Terraform state bucket name."
  value       = google_storage_bucket.terraform_state.name
}
