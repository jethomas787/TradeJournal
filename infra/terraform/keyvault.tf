# ── Key Vault (RBAC authorization) ───────────────────────────
resource "azurerm_key_vault" "kv" {
  name                        = "kv-tradejournal-${random_string.suffix.result}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enable_rbac_authorization   = true # RBAC — not access policies
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false # Dev: allow purge; Prod: true
  tags                        = local.common_tags
}

# ── RBAC: Terraform SP → Key Vault Secrets Officer ──────────
resource "azurerm_role_assignment" "sp_kv_secrets_officer" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ── RBAC: Personal Account → Key Vault Administrator ────────
resource "azurerm_role_assignment" "personal_kv_admin" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.personal_account_object_id
}

# Wait for RBAC propagation before writing secrets
resource "time_sleep" "kv_rbac_wait" {
  depends_on = [azurerm_role_assignment.sp_kv_secrets_officer]

  create_duration = "90s"
}
resource "azurerm_key_vault_secret" "pg_admin_login" {
  depends_on = [time_sleep.kv_rbac_wait]

  name         = "pg-admin-login"
  value        = var.pg_admin_username
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "pg_admin_password" {
  depends_on = [time_sleep.kv_rbac_wait]

  name         = "pg-admin-password"
  value        = random_password.pg_admin.result
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "pg_connection_string" {
  depends_on = [time_sleep.kv_rbac_wait]

  name         = "pg-connection-string"
  value        = "host=${azurerm_postgresql_flexible_server.pg.fqdn} dbname=tradejournal user=${var.pg_admin_username} password=${random_password.pg_admin.result} sslmode=require"
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  depends_on = [time_sleep.kv_rbac_wait]

  name         = "storage-account-key"
  value        = azurerm_storage_account.adls.primary_access_key
  key_vault_id = azurerm_key_vault.kv.id
}