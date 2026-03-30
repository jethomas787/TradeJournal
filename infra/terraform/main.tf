terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
      resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ── Data sources ──────────────────────────────────────────────
data "azurerm_client_config" "current" {}

# ── Random suffix for globally unique names ───────────────────
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# ── Random password — NEVER written to disk ───────────────────
resource "random_password" "pg_admin" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}|;:,.<>?"
  min_lower        = 4
  min_upper        = 4
  min_numeric      = 4
  min_special      = 4
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-tradejournal-${var.environment}-canadacentral"
  location = var.location
  tags     = local.common_tags
}

# ── ADLS Gen2 Storage Account ─────────────────────────────────
resource "azurerm_storage_account" "adls" {
  name                     = "sadltradejournal${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true # Required for ADLS Gen2
  min_tls_version          = "TLS1_2"
  tags                     = local.common_tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.adls.id
}

# ── PostgreSQL Flexible Server ───────────────────────────────
resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "pg-tradejournal-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "15"
  administrator_login    = var.pg_admin_username
  administrator_password = random_password.pg_admin.result # From random provider
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  backup_retention_days  = 7
  zone                   = "1"
  tags                   = local.common_tags
}

# Allow Azure services to connect (includes AKS pods in later weeks)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Allow your machine IP (replace with your current IP)
resource "azurerm_postgresql_flexible_server_firewall_rule" "dev_machine" {
  name             = "DevMachine"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = var.dev_machine_ip
  end_ip_address   = var.dev_machine_ip
}

resource "azurerm_postgresql_flexible_server_database" "tradejournal" {
  name      = "tradejournal"
  server_id = azurerm_postgresql_flexible_server.pg.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_consumption_budget_resource_group" "tp_budget" {
  name              = "budget-${var.project_prefix}-dev"
  resource_group_id = azurerm_resource_group.rg.id
  amount            = 60 # Monthly total ($15/week baseline)
  time_grain        = "Monthly"

  time_period {
    start_date = "2026-03-01T00:00:00Z" 
  }

  # Alert 1: 50% ($30) - Early Warning
  notification {
    enabled        = true
    threshold      = 50.0
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = ["your-email@example.com"]
  }

  # Alert 2: 75% ($45) - Critical Threshold
  notification {
    enabled        = true
    threshold      = 75.0
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = ["your-email@example.com"]
  }

  # Alert 3: 90% ($54) - Near Limit
  notification {
    enabled        = true
    threshold      = 90.0
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = ["your-email@example.com"]
  }

  # Alert 4: Forecasted 100% ($60) - Predictive
  notification {
    enabled        = true
    threshold      = 100.0
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = ["your-email@example.com"]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}
