from typing import Any

import httpx

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools._inputs import path_identifier, required_text


class AsqavProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            api_key = required_text(credentials, "asqav_api_key")
            agent_id = path_identifier(credentials, "asqav_agent_id")
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
                f"Failed to validate credentials: {e!s}"
            ) from e
