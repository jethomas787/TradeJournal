import logging
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)

class SecretManager:
    def __init__(self, vault_url:str) -> None:
        if not vault_url or not vault_url.startswith("https://"):
            raise ValueError(
                f"vault_url must be an HTTPS URL. Received: '{vault_url}'"
            )
        self._client = SecretClient(
            vault_url=vault_url,
            credential=DefaultAzureCredential()
        )
    def get(self,secret_name: str) -> str:
        if not secret_name or not secret_name.strip():
            raise ValueError("secret_name must be a non-empty string")
        try:
            value = self._client.get_secret(secret_name).value
            if not value:
                raise ValueError(
                    f"Secret '(secret_name)' was retrieved but contans no value."
                    "Check the Key Vault entry"
                )
            return value
        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Key Vault retrieval failed for secret '%s',"
                "Check OIDC identity permission and vault access policy.",
                secret_name
            )
            raise RuntimeError(
                f"Failed to retrieved secret '{secret_name}' from Key Vault" 
            )from exc
        