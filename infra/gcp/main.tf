locals {
  db_name = "hr"
  db_user = "app"
  image   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.api.repository_id}/api:${var.image_tag}"
}

# ---------- APIs ----------
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ---------- Artifact Registry ----------
resource "google_artifact_registry_repository" "api" {
  repository_id = var.name
  location      = var.region
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# ---------- Cloud SQL (PostgreSQL) ----------
resource "google_sql_database_instance" "postgres" {
  name                = "${var.name}-pg"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = false

  settings {
    tier      = var.db_tier
    edition   = "ENTERPRISE"
    disk_size = 10

    ip_configuration {
      # Public IP without authorized networks: only reachable through the
      # Cloud SQL connector that Cloud Run uses (IAM-authorized).
      ipv4_enabled = true
    }

    backup_configuration {
      enabled = false
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_sql_database" "hr" {
  name     = local.db_name
  instance = google_sql_database_instance.postgres.name
}

resource "random_password" "db" {
  length  = 32
  special = false # keeps the password URL-safe inside DATABASE_URL
}

resource "google_sql_user" "app" {
  name     = local.db_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.db.result
}

# ---------- Secret Manager (DATABASE_URL) ----------
resource "google_secret_manager_secret" "db_url" {
  secret_id = "${var.name}-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_url" {
  secret = google_secret_manager_secret.db_url.id
  # Connects through the Unix socket Cloud Run mounts at /cloudsql
  secret_data = "postgresql+psycopg://${local.db_user}:${random_password.db.result}@/${local.db_name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
}

# ---------- Service account for Cloud Run ----------
resource "google_service_account" "api" {
  account_id   = "${var.name}-api"
  display_name = "DB Migration API (Cloud Run)"
}

resource "google_project_iam_member" "api_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "api_db_url" {
  secret_id = google_secret_manager_secret.db_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

# ---------- Cloud Run ----------
resource "google_cloud_run_v2_service" "api" {
  name                = "${var.name}-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }

    containers {
      image = local.image

      ports {
        container_port = 8000
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 12
      }
    }
  }

  depends_on = [
    google_project_iam_member.api_sql_client,
    google_secret_manager_secret_iam_member.api_db_url,
    google_secret_manager_secret_version.db_url,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_unauthenticated ? 1 : 0
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
