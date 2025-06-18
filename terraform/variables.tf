# -------------------------------------
# General GCP Configuration
# -------------------------------------
variable "project_id" {
  description = "The GCP project ID to deploy resources in."
  type        = string
  default     = "ai-powered-lms" # Default based on your gcloud config
}

variable "region" {
  description = "The GCP region for resources like Cloud SQL and Cloud Run."
  type        = string
  default     = "us-central1" # Default based on your gcloud config
}

# -------------------------------------
# Cloud SQL Configuration
# -------------------------------------
variable "instance_name" {
  description = "The name of the Cloud SQL instance."
  type        = string
  default     = "cloudnative-lms-instance"
}

variable "database_name" {
  description = "The name of the database to create."
  type        = string
  default     = "cloudnative_lms"
}

variable "db_user_name" {
  description = "The username for the database user."
  type        = string
  default     = "lms_user"
}

variable "db_engine" {
  description = "The database engine type ('MYSQL' or 'MARIADB')."
  type        = string
  default     = "MYSQL" # Or "MARIADB"

  validation {
    condition     = contains(["MYSQL", "MARIADB"], var.db_engine)
    error_message = "Allowed values for db_engine are MYSQL or MARIADB."
  }
}

variable "db_version_mysql" {
  description = "The MySQL database version (e.g., MYSQL_8_0, MYSQL_5_7)."
  type        = string
  default     = "MYSQL_8_0"
}

variable "db_version_mariadb" {
  description = "The MariaDB database version (e.g., MARIADB_10_6, MARIADB_10_5)."
  type        = string
  default     = "MARIADB_10_6"
}

variable "db_tier" {
  description = "The machine type for the Cloud SQL instance (e.g., db-f1-micro, db-g1-small, db-n1-standard-1)."
  type        = string
  default     = "db-f1-micro"
}

variable "authorized_networks" {
  description = "List of authorized networks (CIDR notation) allowed to connect. Use ['0.0.0.0/0'] for public access (NOT recommended for production)."
  type        = list(object({ name = string, value = string }))
  default     = [] # Example: [{ name = "allow-all", value = "0.0.0.0/0" }] - CONFIGURE THIS!
}

variable "deletion_protection" {
  description = "Enable deletion protection for the Cloud SQL instance."
  type        = bool
  default     = false # Set to true for production
}

variable "enable_backups" {
  description = "Enable automated backups for the Cloud SQL instance."
  type        = bool
  default     = true
}

variable "store_password_in_secret_manager" {
  description = "Set to true to store the generated database password in Secret Manager."
  type        = bool
  default     = true
}

# -------------------------------------
# Application Specific Configuration
# -------------------------------------
variable "gcs_bucket_name" {
  description = "Name of the GCS bucket used by the application."
  type        = string
  default     = "lms-ai"
}

variable "jwt_expiry_minutes" {
  description = "JWT token expiry duration in minutes."
  type        = number
  default     = 30
}

variable "vertex_ai_model" {
  description = "The Vertex AI model name used by the application."
  type        = string
  default     = "gemini-2.5-pro-exp-03-25"
}

variable "app_secret_key_value" {
  description = "The actual secret key for the application. If left empty, a random one will be generated. IMPORTANT: For production, set this explicitly via tfvars or env var and manage securely."
  type        = string
  default     = "" # Leave empty to trigger random generation for non-production
  sensitive   = true
}

variable "app_secret_key_secret_id" {
  description = "The Secret Manager secret ID for storing the application's SECRET_KEY."
  type        = string
  default     = "lms-app-secret-key"
}

# -------------------------------------
# Cloud Run Configuration
# -------------------------------------
variable "cloudrun_service_name" {
  description = "The name for the Cloud Run service."
  type        = string
  default     = "lms-backend-service"
}

variable "cloudrun_service_account_id" {
  description = "The ID for the dedicated service account for Cloud Run (must be unique within project)."
  type        = string
  default     = "lms-cloudrun-sa" # Keep it short
}

variable "cloudrun_allow_unauthenticated" {
  description = "Allow unauthenticated access to the Cloud Run service (make it public)."
  type        = bool
  default     = true # Set to false if you want IAM-controlled access
}

variable "cloudrun_min_instances" {
  description = "Minimum number of container instances for the service."
  type        = number
  default     = 0 # Set > 0 to avoid cold starts, but incurs cost
}

variable "cloudrun_max_instances" {
  description = "Maximum number of container instances for the service."
  type        = number
  default     = 2 # Adjust based on expected load
}

variable "cloudrun_container_concurrency" {
  description = "Number of requests that can be processed concurrently by a single container instance."
  type        = number
  default     = 80 # Default for Cloud Run
}

variable "cloudrun_cpu_limit" {
  description = "CPU limit for the container instance (e.g., '1', '2', '4'). Affects cost."
  type        = string
  default     = "1" # 1 vCPU
}

variable "cloudrun_memory_limit" {
  description = "Memory limit for the container instance (e.g., '512Mi', '1Gi', '2Gi'). Affects cost."
  type        = string
  default     = "512Mi" # 512 MB - Adjust based on application needs
}
