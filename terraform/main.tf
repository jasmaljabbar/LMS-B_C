terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Constrained to 5.x versions
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -------------------------------------
# API Enablement
# -------------------------------------
# ... (API enablement resources remain the same) ...
resource "google_project_service" "sqladmin_api" {
  project            = var.project_id
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager_api" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run_api" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam_api" {
  project            = var.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "aiplatform_api" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# -------------------------------------
# Database Password Generation & Secret
# -------------------------------------
# ... (db password and secret resources remain the same) ...
resource "random_password" "db_password" {
  length           = 20
  special          = true
  override_special = "_%@"
}

resource "google_secret_manager_secret" "db_password_secret" {
  count     = var.store_password_in_secret_manager ? 1 : 0
  project   = var.project_id
  secret_id = "${var.instance_name}-db-password"

  replication {
    user_managed {
      replicas { location = "us-central1" }
      replicas { location = "us-east1" }
    }
  }
  depends_on = [google_project_service.secretmanager_api]
}

resource "google_secret_manager_secret_version" "db_password_secret_version" {
  count       = var.store_password_in_secret_manager ? 1 : 0
  secret      = google_secret_manager_secret.db_password_secret[0].id
  secret_data = random_password.db_password.result
  depends_on = [
    google_secret_manager_secret.db_password_secret,
    random_password.db_password
  ]
}

# -------------------------------------
# Cloud SQL Instance, Database, User
# -------------------------------------
# ... (Cloud SQL resources remain the same) ...
resource "google_sql_database_instance" "main" {
  project            = var.project_id
  name               = var.instance_name
  region             = var.region
  database_version   = var.db_engine == "MYSQL" ? var.db_version_mysql : var.db_version_mariadb
  deletion_protection = var.deletion_protection

  settings {
    tier = var.db_tier
    ip_configuration {
      ipv4_enabled = true
      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
      # require_ssl = true
    }
    backup_configuration {
      enabled            = var.enable_backups
      binary_log_enabled = var.enable_backups
    }
  }
  depends_on = [google_project_service.sqladmin_api]
}

resource "google_sql_database" "main_db" {
  project  = var.project_id
  name     = var.database_name
  instance = google_sql_database_instance.main.name
  depends_on = [google_sql_database_instance.main]
}

resource "google_sql_user" "main_user" {
  project  = var.project_id
  name     = var.db_user_name
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
  depends_on = [
    google_sql_database_instance.main,
    random_password.db_password
  ]
}

# -------------------------------------
# Application Secret Key Management
# -------------------------------------
# ... (app secret key resources remain the same) ...
resource "random_string" "app_secret_key_random" {
  count   = var.app_secret_key_value == "" ? 1 : 0
  length  = 48
  special = true
}

locals {
  app_secret_key = var.app_secret_key_value != "" ? var.app_secret_key_value : (length(random_string.app_secret_key_random) > 0 ? random_string.app_secret_key_random[0].result : "fallback-insecure-key-${timestamp()}")
}

resource "google_secret_manager_secret" "app_secret_key" {
  project   = var.project_id
  secret_id = var.app_secret_key_secret_id
  replication {
    user_managed {
      replicas { location = "us-central1" }
      replicas { location = "us-east1" }
    }
  }
  depends_on = [google_project_service.secretmanager_api]
}

resource "google_secret_manager_secret_version" "app_secret_key_version" {
  secret      = google_secret_manager_secret.app_secret_key.id
  secret_data = local.app_secret_key
  depends_on = [google_secret_manager_secret.app_secret_key]
  lifecycle { prevent_destroy = false }
}

# -------------------------------------
# Cloud Run Service Account & IAM
# -------------------------------------
# ... (service account and IAM bindings remain the same) ...
resource "google_service_account" "cloudrun_sa" {
  project      = var.project_id
  account_id   = var.cloudrun_service_account_id
  display_name = "LMS Backend Cloud Run Service Account"
  description  = "Service Account for the LMS Backend Cloud Run service"
}

resource "google_project_iam_member" "cloudrun_sa_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
  depends_on = [google_project_service.sqladmin_api, google_service_account.cloudrun_sa]
}

resource "google_project_iam_member" "cloudrun_sa_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
  depends_on = [google_project_service.secretmanager_api, google_service_account.cloudrun_sa]
}

resource "google_project_iam_member" "cloudrun_sa_gcs_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
  depends_on = [google_service_account.cloudrun_sa]
}

resource "google_project_iam_member" "cloudrun_sa_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloudrun_sa.email}"
  depends_on = [google_project_service.aiplatform_api, google_service_account.cloudrun_sa]
}

# -------------------------------------
# Cloud Run Service Definition
# -------------------------------------
resource "google_cloud_run_v2_service" "main" {
  project  = var.project_id
  name     = var.cloudrun_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloudrun_sa.email

    scaling {
      min_instance_count = var.cloudrun_min_instances
      max_instance_count = var.cloudrun_max_instances
    }

    containers {
      # --- Main Application Container ---
      name  = "lms-backend-app"
      image = "docker.io/rathinamtrainers/lmsai:latest"
      ports { container_port = 8000 }
      resources {
        limits = { cpu = var.cloudrun_cpu_limit, memory = var.cloudrun_memory_limit }
        startup_cpu_boost = true
      }

      # --- Environment Variables ---
      env {
        name  = "DATABASE_URL"
        value = "mysql+pymysql://${var.db_user_name}@127.0.0.1:3306/${var.database_name}"
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.store_password_in_secret_manager ? google_secret_manager_secret.db_password_secret[0].secret_id : "unused-db-secret"
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secret_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = var.gcs_bucket_name
      }
      env {
        name  = "JWT_EXPIRY_MINUTES"
        value = tostring(var.jwt_expiry_minutes)
      }
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "LOCATION"
        value = var.region
      }
      env {
        name  = "MODEL_NAME"
        value = var.vertex_ai_model
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "VERTEX_AI_LOCATION"
        value = var.region
      }
      env {
        name  = "VERTEX_AI_MODEL"
        value = var.vertex_ai_model
      }

      # startup_probe { ... }
      # liveness_probe { ... }
    } # End of Application Container

    containers {
      # --- Cloud SQL Proxy Sidecar Container ---
      name  = "cloud-sql-proxy"
      image = "gcr.io/cloud-sql-connectors/cloud-sql-proxy:latest"
      args = [
        "--structured-logs",
        "--instances=${google_sql_database_instance.main.connection_name}=tcp:3306"
      ]
      resources { limits = { cpu = "1", memory = "256Mi" } }
      # --- REMOVED security_context block ---
      # security_context { run_as_non_root = true }
    } # End of Cloud SQL Proxy Container
  } # End template

  depends_on = [
    google_project_service.run_api,
    google_project_iam_member.cloudrun_sa_sql_client,
    google_project_iam_member.cloudrun_sa_secret_accessor,
    google_project_iam_member.cloudrun_sa_gcs_access,
    google_project_iam_member.cloudrun_sa_vertex_user,
    google_secret_manager_secret_version.app_secret_key_version,
    google_sql_database_instance.main,
    google_sql_user.main_user,
  ]
}

# -------------------------------------
# IAM Binding for Public Access (Conditional)
# -------------------------------------
resource "google_cloud_run_v2_service_iam_member" "allow_public" {
  count    = var.cloudrun_allow_unauthenticated ? 1 : 0
  project  = google_cloud_run_v2_service.main.project
  location = google_cloud_run_v2_service.main.location
  name     = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = "allUsers"
  depends_on = [google_cloud_run_v2_service.main]
}
