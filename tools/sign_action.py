import json
from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

API_BASE = "https://api.asqav.com/api/v1"


class SignActionTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        api_key = self.runtime.credentials["asqav_api_key"]
        agent_id = self.runtime.credentials["asqav_agent_id"]
        action_type = tool_parameters["action_type"]
        context_str = tool_parameters.get("context", "")

        context = {}
        if context_str:
            try:
                context = json.loads(context_str)
            except json.JSONDecodeError:
                context = {"raw": context_str}

        response = httpx.post(
            f"{API_BASE}/agents/{agent_id}/sign",
            headers={"X-API-Key": api_key},
            json={
                "action_type": action_type,
                "context": context,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        yield self.create_json_message({
            "signature_id": data["signature_id"],
            "action_id": data["action_id"],
            "timestamp": data["timestamp"],
            "verification_url": data["verification_url"],
        })
