# Terraform configuration for GCP Cloud Run deployment
# SPARQL Agent Infrastructure

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "sparql-agent-terraform-state"
    prefix = "cloud-run"
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# Variables
variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "sparql-agent"
}

variable "app_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "2"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "2Gi"
}

# Cloud Run Service
resource "google_cloud_run_service" "main" {
  name     = "${var.app_name}-${var.environment}"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = var.app_image

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }

        ports {
          container_port = 8000
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "PORT"
          value = "8000"
        }

        liveness_probe {
          http_get {
            path = "/health"
          }
          initial_delay_seconds = 30
          period_seconds        = 30
        }
      }

      service_account_name = google_service_account.cloudrun.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true
}

# IAM policy to allow unauthenticated access
resource "google_cloud_run_service_iam_member" "public" {
  count = var.environment != "production" ? 1 : 0

  service  = google_cloud_run_service.main.name
  location = google_cloud_run_service.main.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service Account
resource "google_service_account" "cloudrun" {
  account_id   = "${var.app_name}-${var.environment}-sa"
  display_name = "Service Account for ${var.app_name} ${var.environment}"
}

# Cloud SQL (optional)
resource "google_sql_database_instance" "main" {
  count = var.environment == "production" ? 1 : 0

  name             = "${var.app_name}-${var.environment}-db"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier = "db-f1-micro"

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.main[0].id
    }
  }

  deletion_protection = true
}

# VPC Network (for Cloud SQL)
resource "google_compute_network" "main" {
  count = var.environment == "production" ? 1 : 0

  name                    = "${var.app_name}-${var.environment}-network"
  auto_create_subnetworks = true
}

# Outputs
output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_service.main.status[0].url
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_service.main.name
}
