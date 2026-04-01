import os
import re
import subprocess
from pathlib import Path
import pytest

from azure.identity import DefaultAzureCredentialpi
from azure.keyvault.secrets import SecretClient
from sqlalchemy import create_engine, text

def get_key_vault_uri() -> str:
    """
    Retrieves the Key Vault URI. 
    Prioritizes environment variables (CI/CD) then falls back to 
    local Terraform output.
    """
    uri = os.environ.get("KEY_VAULT_URI")
    if uri:
        return uri

    # Local development fallback: Query Terraform for the URI
    result = subprocess.run(
        ["terraform", "output", "-raw", "key_vault_uri"],
        cwd="infra/terraform",
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def get_engine():
    """
    Establishes a SQLAlchemy engine using Azure Identity.
    Supports: Environment Vars, Workload Identity, Managed Identity, and Azure CLI.
    """
    kv_uri = get_key_vault_uri()
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)
    
    # Connection string includes 'sslmode=require' via Key Vault configuration
    conn_str = client.get_secret("pg-connection-string").value
    return create_engine(conn_str)

if __name__ == "__main__":
    engine = get_engine()
    
    # Locate and sort all DDL scripts to ensure dependency order (e.g., 01 before 02)
    sql_dir = Path("sql/ddl")
    scripts = sorted(sql_dir.glob("*.sql"))

    if not scripts:
        print(f"Error: No .sql files found in {sql_dir}")
        raise SystemExit(1)

    print(f"Found {len(scripts)} scripts. Starting execution...")

    # Use a single transaction block for the entire execution run
    for script in scripts:
        print(f" -> Executing: {script.name}")
        
        with engine.begin() as conn:
            sql_content = script.read_text()
            conn.execute(text(sql_content))

    print("\nSuccess: All DDL scripts applied.")