# ──────────────────────────────────────────────────────────────────────────────
# AI ATS — Terraform Infrastructure as Code
# Resources: GKE cluster, Cloud SQL (PostgreSQL+pgvector), Memorystore (Redis),
#            Artifact Registry, Service Accounts, Network
# ──────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.15"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── Networking ───────────────────────────────────────────────────────────────

resource "google_compute_network" "vpc" {
  name                    = "ai-ats-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "ai-ats-subnet"
  network       = google_compute_network.vpc.id
  region        = var.region
  ip_cidr_range = "10.0.0.0/16"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# ─── GKE Cluster ──────────────────────────────────────────────────────────────

resource "google_container_cluster" "primary" {
  name     = "ai-ats-cluster"
  location = var.zone

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.subnet.id

  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "primary" {
  name       = "ai-ats-node-pool"
  cluster    = google_container_cluster.primary.id
  location   = var.zone
  node_count = var.node_count

  autoscaling {
    min_node_count = var.min_nodes
    max_node_count = var.max_nodes
  }

  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ─── Cloud SQL (PostgreSQL + pgvector) ────────────────────────────────────────

resource "google_sql_database_instance" "postgres" {
  name             = "ai-ats-postgres"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-custom-2-8192"  # 2 vCPU, 8 GB RAM
    disk_size         = 100
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    disk_autoresize_limit = 500

    database_flags {
      name  = "max_connections"
      value = "200"
    }
    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,vector"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.vpc.id
    }

    maintenance_window {
      day  = 7  # Sunday
      hour = 4
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "app" {
  name     = "resume_db"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "ats_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# ─── Memorystore (Redis) ──────────────────────────────────────────────────────

resource "google_redis_instance" "cache" {
  name           = "ai-ats-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = 2
  region         = var.region

  redis_version     = "REDIS_7_0"
  display_name      = "AI ATS Cache"
  authorized_network = google_compute_network.vpc.id

  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "TWENTY_FOUR_HOURS"
  }
}

# ─── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "ai-ats-docker"
  format        = "DOCKER"
}

# ─── Service Accounts ─────────────────────────────────────────────────────────

resource "google_service_account" "app" {
  account_id   = "ai-ats-app"
  display_name = "AI ATS Application SA"
}

resource "google_project_iam_member" "app_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_project_iam_member" "app_redis" {
  project = var.project_id
  role    = "roles/redis.admin"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "postgres_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "db_password_secret" {
  value     = random_password.db_password.result
  sensitive = true
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.name}"
}
