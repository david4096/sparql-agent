# Terraform configuration for Azure Container Instances deployment
# SPARQL Agent Infrastructure

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "sparqlagenttfstate"
    container_name       = "tfstate"
    key                  = "azure-aci.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# Variables
variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
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

variable "cpu" {
  description = "CPU cores"
  type        = number
  default     = 2
}

variable "memory" {
  description = "Memory in GB"
  type        = number
  default     = 4
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.app_name}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

# Container Instance
resource "azurerm_container_group" "main" {
  name                = "${var.app_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  dns_name_label      = "${var.app_name}-${var.environment}"
  restart_policy      = "Always"

  container {
    name   = var.app_name
    image  = var.app_image
    cpu    = var.cpu
    memory = var.memory

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      ENVIRONMENT = var.environment
      PORT        = "8000"
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = 8000
        scheme = "Http"
      }
      initial_delay_seconds = 30
      period_seconds        = 30
    }

    readiness_probe {
      http_get {
        path   = "/ready"
        port   = 8000
        scheme = "Http"
      }
      initial_delay_seconds = 10
      period_seconds        = 10
    }
  }

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

# Outputs
output "fqdn" {
  description = "FQDN of the container group"
  value       = azurerm_container_group.main.fqdn
}

output "ip_address" {
  description = "IP address of the container group"
  value       = azurerm_container_group.main.ip_address
}
