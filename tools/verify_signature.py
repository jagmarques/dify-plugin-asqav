from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

API_BASE = "https://api.asqav.com/api/v1"


class VerifySignatureTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        signature_id = tool_parameters["signature_id"]

        response = httpx.get(
            f"{API_BASE}/verify/{signature_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        yield self.create_json_message({
            "verified": data["verified"],
            "signature_id": data["signature_id"],
            "agent_id": data["agent_id"],
            "agent_name": data["agent_name"],
            "action_type": data["action_type"],
            "algorithm": data["algorithm"],
            "signed_at": data["signed_at"],
            "verification_url": data["verification_url"],
        })
