from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._inputs import path_identifier
from tools._outputs import emit
from tools._responses import response_payload

API_BASE = "https://api.asqav.com/api/v1"


class VerifySignatureTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        signature_id = path_identifier(tool_parameters, "signature_id")

        response = httpx.get(
            f"{API_BASE}/verify/{signature_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        yield from emit(self, response_payload(data, "Verify Signature", (
            ("verified", "flag"), ("signature_id", "text"),
            ("agent_id", "text_or_null"), ("agent_name", "text_or_null"),
            ("action_type", "text_or_null"), ("algorithm", "text"),
            ("signed_at", "text"), ("verification_url", "text"),
        )))
