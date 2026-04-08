import json
from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

API_BASE = "https://api.asqav.com/api/v1"


class RequestActionTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        api_key = self.runtime.credentials["asqav_api_key"]
        agent_id = self.runtime.credentials["asqav_agent_id"]
        action_type = tool_parameters["action_type"]
        params_str = tool_parameters.get("params", "")

        body: dict[str, Any] = {
            "agent_id": agent_id,
            "action_type": action_type,
        }
        if params_str:
            try:
                body["params"] = json.loads(params_str)
            except json.JSONDecodeError:
                body["params"] = {"raw": params_str}

        response = httpx.post(
            f"{API_BASE}/signing-groups/sessions",
            headers={"X-API-Key": api_key},
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        yield self.create_json_message({
            "session_id": data["session_id"],
            "status": data["status"],
            "approvals_required": data["approvals_required"],
            "signatures_collected": data["signatures_collected"],
            "action_type": data["action_type"],
            "created_at": data["created_at"],
            "expires_at": data["expires_at"],
        })
