from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._inputs import object_parameter, path_identifier, required_text
from tools._outputs import emit
from tools._responses import optional_text, response_payload

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
        api_key = required_text(self.runtime.credentials, "asqav_api_key")
        agent_id = path_identifier(self.runtime.credentials, "asqav_agent_id")
        action_type = required_text(tool_parameters, "action_type")
        context = object_parameter(tool_parameters, "context")
        action_ref = tool_parameters.get("action_ref")
        if action_ref is not None and action_ref != "":
            action_ref = required_text(tool_parameters, "action_ref")

        body: dict[str, Any] = {"action_type": action_type, "context": context}
        # Same action_ref on a pre-action and a post-action sign links the two receipts.
        if action_ref:
            body["action_ref"] = action_ref

        response = httpx.post(
            f"{API_BASE}/agents/{agent_id}/sign",
            headers={"X-API-Key": api_key},
            json=body,
            timeout=30.0,
        )

        # A 403 is a policy decision the workflow can branch on; other non-2xx stays loud below.
        if response.status_code == 403:
            yield from emit(self, _denied_result(response))
            return

        response.raise_for_status()
        data = response.json()

        result = response_payload(data, "Sign Action", (
            ("signature_id", "text"), ("action_id", "text"),
            ("timestamp", "number"), ("verification_url", "text"),
        ))
        result["signature_b64"] = optional_text(data, "signature_b64", "Sign Action")
        yield from emit(self, {"authorized": True, **result})


def _denied_result(response: httpx.Response) -> dict[str, Any]:
    """Normalize a 403 refusal into a branchable ``authorized=false`` result.

    The Asqav cloud returns two ``detail`` shapes for a refused sign: a dict
    ``{"error", "attestation_hash", "signed_deny"}`` for a policy or content
    block, or a plain string for emergency halt, delegation, and quarantine
    refusals. A policy block may carry a signed denial receipt (``signed_deny``).
    Both shapes map to ``authorized=false``.
    """
    try:
        detail: Any = response.json().get("detail")
    except (ValueError, KeyError, AttributeError):
        detail = None

    if isinstance(detail, dict):
        is_policy = detail.get("error") == "action_denied"
        fields = response_payload({
            "detail": detail.get("error", "action_denied"),
            "attestation_hash": detail.get("attestation_hash"),
            "denial_signature_id": detail.get("denial_signature_id"),
            "signed_deny": detail.get("signed_deny"),
        }, "Sign Action", (
            ("detail", "text"), ("attestation_hash", "text_or_null"),
            ("denial_signature_id", "text_or_null"), ("signed_deny", "object_or_null"),
        ))
        return {
            "authorized": False,
            "reason": "policy_blocked" if is_policy else "denied",
            **fields,
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
        "denial_signature_id": None,
        "signed_deny": None,
    }
