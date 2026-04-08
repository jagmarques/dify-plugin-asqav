from typing import Any

import httpx

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class AsqavProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = credentials.get("asqav_api_key", "")
        agent_id = credentials.get("asqav_agent_id", "")

        if not api_key:
            raise ToolProviderCredentialValidationError("asqav API key is required")
        if not agent_id:
            raise ToolProviderCredentialValidationError("Agent ID is required")

        try:
            response = httpx.get(
                f"https://api.asqav.com/api/v1/agents/{agent_id}",
                headers={"X-API-Key": api_key},
                timeout=15.0,
            )
            if response.status_code == 401:
                raise ToolProviderCredentialValidationError("Invalid API key")
            if response.status_code == 404:
                raise ToolProviderCredentialValidationError("Agent not found")
            response.raise_for_status()
        except ToolProviderCredentialValidationError:
            raise
        except Exception as e:
            raise ToolProviderCredentialValidationError(
                f"Failed to validate credentials: {str(e)}"
            )
