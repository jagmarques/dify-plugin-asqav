from collections.abc import Generator
from typing import Any

import httpx

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._inputs import path_identifier
from tools._outputs import emit
from tools._responses import response_payload
from tools._verification import bound_evidence, hosted_evidence
from tools._profile import canonical, profile_response, strict_object

API_BASE = "https://api.asqav.com/api/v1"


class VerifySignatureTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        signature_id = path_identifier(tool_parameters, "signature_id")
        receipt_json = tool_parameters.get("receipt_json")
        if receipt_json not in (None, ""):
            yield from emit(self, _verify_receipt(signature_id, receipt_json, tool_parameters))
            return
        if tool_parameters.get("context_json") not in (None, ""):
            raise ValueError("context_json requires receipt_json")

        response = httpx.get(
            f"{API_BASE}/verify/{signature_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        result = response_payload(data, "Verify Signature", (
            ("verified", "flag"), ("signature_id", "text"),
            ("agent_id", "text_or_null"), ("agent_name", "text_or_null"),
            ("action_type", "text_or_null"), ("algorithm", "text"),
            ("signed_at", "text"), ("verification_url", "text"),
        ))
        if result["signature_id"] != signature_id:
            raise ValueError("Verify Signature returned a different signature ID")
        yield from emit(self, {**result, **hosted_evidence(data)})


def _verify_receipt(signature_id: str, original: str, parameters: dict[str, Any]) -> dict[str, Any]:
    receipt = strict_object(original)
    if not {"payload", "signature"} <= set(receipt) <= {"payload", "signature", "anchors"}:
        raise ValueError("receipt_json must contain the original payload, signature and optional anchors")
    context = parameters.get("context_json")
    if context not in (None, ""):
        context = canonical(strict_object(context)).decode("utf-8")
    else:
        context = None
    refresh = parameters.get("refresh_anchors", False)
    if type(refresh) is not bool:
        raise ValueError("refresh_anchors must be a boolean")
    verified_receipt = _refresh_anchors(signature_id, receipt) if refresh else receipt
    body = {"format": "asqav-native", "signature_id": signature_id,
            "receipt": canonical(verified_receipt).decode("utf-8"), "context_json": context}
    response = httpx.post(f"{API_BASE}/verify/universal", json=body, timeout=30.0)
    response.raise_for_status()
    result = bound_evidence(profile_response(response.text), verified_receipt, context is not None)
    return {**result, "signature_id": signature_id, "receipt_json": original,
            "verified_receipt_json": body["receipt"],
            "anchors_refreshed": canonical(receipt) != canonical(verified_receipt),
            "verification_url": f"{API_BASE}/verify/{signature_id}"}


def _refresh_anchors(signature_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
    response = httpx.get(f"{API_BASE}/verify/{signature_id}", timeout=30.0)
    response.raise_for_status()
    data = profile_response(response.text)
    if data.get("signature_id") != signature_id:
        raise ValueError("Verify Signature returned a different signature ID")
    anchors = data.get("anchors")
    if not isinstance(anchors, list) or any(not isinstance(a, dict) for a in anchors):
        raise ValueError("Verify Signature returned malformed anchor proofs")
    return {**receipt, "anchors": anchors}
