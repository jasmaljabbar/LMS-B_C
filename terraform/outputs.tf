# -------------------------------------
# Cloud SQL Outputs
# -------------------------------------
output "instance_name" {
  description = "The name of the Cloud SQL instance."
  value       = google_sql_database_instance.main.name
}

output "instance_connection_name" {
  description = "The connection name of the Cloud SQL instance (used by Cloud SQL Proxy)."
  value       = google_sql_database_instance.main.connection_name
}

output "instance_public_ip_address" {
  description = "The public IP address of the Cloud SQL instance (if enabled)."
  value       = google_sql_database_instance.main.public_ip_address
}

output "instance_private_ip_address" {
  description = "The private IP address of the Cloud SQL instance (if enabled)."
  value       = google_sql_database_instance.main.private_ip_address
}

output "database_name" {
  description = "The name of the database created."
  value       = google_sql_database.main_db.name
}

output "database_user_name" {
  description = "The username created for the database."
  value       = google_sql_user.main_user.name
}

output "database_password_secret_id" {
  description = "The Secret Manager secret ID where the database password is stored (if enabled)."
  # Handle the case where the secret resource might not be created due to count=0
  value       = var.store_password_in_secret_manager ? google_secret_manager_secret.db_password_secret[0].secret_id : "Password not stored in Secret Manager."
  sensitive   = true
}

output "generated_database_password" {
  description = "The randomly generated password for the database user (output only if not stored in Secret Manager)."
  value       = var.store_password_in_secret_manager ? "Stored in Secret Manager" : random_password.db_password.result
  sensitive   = true
}

# -------------------------------------
# Cloud Run Deployment Outputs
# -------------------------------------
output "cloudrun_service_name" {
  description = "The name of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.main.name
}

output "cloudrun_service_url" {
  description = "The URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.main.uri
}

output "cloudrun_service_account_email" {
  description = "The email of the service account used by Cloud Run."
  value       = google_service_account.cloudrun_sa.email
}

output "app_secret_key_secret_id" {
  description = "The Secret Manager secret ID for the application's SECRET_KEY."
  value       = google_secret_manager_secret.app_secret_key.secret_id
}
