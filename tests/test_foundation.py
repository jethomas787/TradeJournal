""" 
Week 1 smoke tests — all 5 must pass before Week 2 begins. 
Run: pytest tests/test_foundation.py -v 
"""

import os
import re
import subprocess
from pathlib import Path
import pytestwhic

@pytest.fixture(scope="session")
def engine():
    """SQLAlchemy engine via Key Vault — same DefaultAzureCredential pattern."""
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from sqlalchemy import create_engine

    # Retrieve Key Vault URI from Env or Terraform
    kv_uri = os.environ.get("KEY_VAULT_URI") or subprocess.run(
        ["terraform", "output", "-raw", "key_vault_uri"],
        cwd="infra/terraform",
        capture_output=True,
        text=True
    ).stdout.strip()

    cred = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=cred)
    
    # Retrieve connection string directly from Azure Key Vault
    conn_str = client.get_secret("pg-connection-string").value
    return create_engine(conn_str)


def test_five_tables_exist(engine):
    """trading schema must contain exactly 5 tables."""
    from sqlalchemy import text
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'trading' ORDER BY table_name"
        )).fetchall()
        
        names = {r[0] for r in rows}
        expected = {"instruments", "accounts", "trades", "positions", "market_prices"}
        assert names == expected, f"Unexpected tables: {names}"


def test_trades_computed_column(engine):
    """gross_value must be a GENERATED ALWAYS AS STORED column."""
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT is_generated FROM information_schema.columns "
            "WHERE table_schema='trading' AND table_name='trades' "
            "AND column_name='gross_value'"
        )).fetchone()
        
        assert row is not None, "gross_value column not found"
        assert row[0] == "ALWAYS", f"Expected ALWAYS, got {row[0]}"


def test_ssl_connection(engine):
    """Connection must use SSL (sslmode=require baked into conn string)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check if the current PostgreSQL session is encrypted
        result = conn.execute(text("SELECT ssl_is_used()")).scalar()
        assert result is True, "SSL is not active on this connection"


def test_simulator_output_exists():
    """Simulator must have produced at least one JSONL file."""
    files = list(Path("simulator/output").glob("*.jsonl"))
    assert len(files) > 0, "No simulator output found — run trade_generator.py first"


def test_no_hardcoded_credentials():
    """No source file may contain a hardcoded password or connection string."""
    suspicious = re.compile(
        r"(password\s*=\s*['\"][\w\d]+['\"])|"
        r"postgresql://\S+:\S+@|"
        r"ARM_CLIENT_SECRET\s*=\s*['\"][^']+",
        re.IGNORECASE
    )
    
    skip_files = {".env", "terraform.tfvars", ".tfstate"}
    skip_dirs = {"__pycache__", ".terraform", ".git"}

    for p in Path(".").rglob("*"):
        # Only check code and config files
        if p.is_file() and p.suffix in {".py", ".tf", ".yml", ".yaml", ".sh"}:
            if any(s in p.parts for s in skip_dirs):
                continue
            if p.name in skip_files:
                continue
            
            content = p.read_text(errors="ignore")
            matches = suspicious.findall(content)
            assert not matches, f"Possible hardcoded credential in {p}: {matches[:2]}"