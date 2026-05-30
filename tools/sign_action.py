import json
from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

API_BASE = "https://api.asqav.com/api/v1"

#: Substring of a string-form 403 detail -> stable machine reason (halt/delegation/quarantine).
_STRING_REASONS: tuple[tuple[str, str], ...] = (
    ("emergency halt", "emergency_halt"),
    ("delegated scope", "delegation_denied"),
    ("delegation has expired", "delegation_denied"),
    ("quarantine", "quarantine"),
)


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

        # A 403 is a policy decision the workflow can branch on; other non-2xx stays loud below.
        if response.status_code == 403:
            yield self.create_json_message(_denied_result(response))
            return

        response.raise_for_status()
        data = response.json()

        yield self.create_json_message({
            "authorized": True,
            "signature_id": data["signature_id"],
            "action_id": data["action_id"],
            "timestamp": data["timestamp"],
            "verification_url": data["verification_url"],
            "signature_b64": data.get("signature_b64"),
        })


def _denied_result(response: httpx.Response) -> dict[str, Any]:
    """Normalize a 403 refusal into a branchable ``authorized=false`` result.

    The Asqav cloud returns two ``detail`` shapes for a refused sign: a dict
    ``{"error", "attestation_hash", "signed_deny"}`` for a policy or content
    block, or a plain string for emergency halt, delegation, and quarantine
    refusals. A policy block carries a signed denial receipt (``signed_deny``)
    that is itself verifiable. Both shapes map to ``authorized=false``; the
    caller never sees this when a signature was actually minted.
    """
    try:
        detail: Any = response.json().get("detail")
    except (ValueError, KeyError, AttributeError):
        detail = None

    if isinstance(detail, dict):
        is_policy = detail.get("error") == "action_denied"
        return {
            "authorized": False,
            "reason": "policy_blocked" if is_policy else "denied",
            "detail": detail.get("error", "action_denied"),
            "attestation_hash": detail.get("attestation_hash"),
            "signed_deny": detail.get("signed_deny"),
        }

    text = detail if isinstance(detail, str) and detail else "Action denied by policy"
    reason = "denied"
    lowered = text.lower()
    for needle, mapped in _STRING_REASONS:
        if needle in lowered:
            reason = mapped
            break
    return {
        "authorized": False,
        "reason": reason,
        "detail": text,
        "attestation_hash": None,
        "signed_deny": None,
    }
