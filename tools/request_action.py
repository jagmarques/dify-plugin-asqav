from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._inputs import object_parameter, path_identifier, required_text
from tools._outputs import emit
from tools._responses import response_payload

API_BASE = "https://api.asqav.com/api/v1"


class RequestActionTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        api_key = required_text(self.runtime.credentials, "asqav_api_key")
        agent_id = path_identifier(self.runtime.credentials, "asqav_agent_id")
        action_type = required_text(tool_parameters, "action_type")
        params = object_parameter(tool_parameters, "params")

        body: dict[str, Any] = {
            "agent_id": agent_id,
            "action_type": action_type,
        }
        if tool_parameters.get("params"):
            body["params"] = params

        response = httpx.post(
            f"{API_BASE}/signing-groups/sessions",
            headers={"X-API-Key": api_key},
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        yield from emit(self, response_payload(data, "Request Action", (
            ("session_id", "text"), ("status", "text"),
            ("approvals_required", "positive_integer"),
            ("signatures_collected", "nonnegative_integer"),
            ("action_type", "text"), ("created_at", "text"), ("expires_at", "text"),
        )))
