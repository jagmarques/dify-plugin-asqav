"""Request and retain profile observations without granting execution authority."""
import hashlib
import json
from typing import Any

import rfc8785

from tools._inputs import required_text
from tools._responses import response_payload

MAX_JSON_BYTES = 1_048_576
MAX_DEPTH = 64
MAX_INTEGER = 2**53 - 1


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Profile JSON must not contain duplicate members")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Profile JSON must contain finite integers, not NaN or Infinity")


def _check_domain(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("Profile JSON nesting exceeds 64 levels")
    if isinstance(value, float):
        raise ValueError("Profile JSON does not allow floating-point numbers")
    if type(value) is int and abs(value) > MAX_INTEGER:
        raise ValueError("Profile JSON integer exceeds the safe integer range")
    if isinstance(value, dict):
        for item in value.values():
            _check_domain(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_domain(item, depth + 1)


def canonical(value: Any) -> bytes:
    _check_domain(value)
    return rfc8785.dumps(value)


def strict_object(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("Profile input must be a JSON object under 1 MiB")
    try:
        result = json.loads(value, object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Profile input must be valid JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("Profile input must be a JSON object")
    canonical(result)
    return result


def profile_response(value: str) -> dict[str, Any]:
    if len(value.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("Sign Action returned a response exceeding 1 MiB")
    try:
        result = json.loads(value, object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Sign Action returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("Sign Action returned a non-object response")
    _check_depth(result)
    return result


def _check_depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ValueError("Profile JSON nesting exceeds 64 levels")
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
    for item in items:
        _check_depth(item, depth + 1)


def signing_mode(parameters: dict[str, Any]) -> str:
    mode = parameters.get("receipt_mode", "standard")
    if mode not in ("standard", "profile"):
        raise ValueError("receipt_mode must be standard or profile")
    return mode


def profile_request(parameters: dict[str, Any], action_type: str) -> dict[str, Any]:
    context = strict_object(parameters.get("context") or "{}")
    iteration_id = required_text(parameters, "iteration_id")
    if len(iteration_id) > 128:
        raise ValueError("iteration_id must contain at most 128 characters")
    action_ref = "sha256:" + hashlib.sha256(canonical({
        "action_type": action_type, "context": context,
    })).hexdigest()
    supplied = parameters.get("action_ref")
    if supplied not in (None, "", action_ref):
        raise ValueError("Profile action_ref must match the canonical action and context")
    return {"action_type": action_type, "context": context,
            "action_ref": action_ref, "iteration_id": iteration_id,
            "compliance_mode": True, "capture_topology": "in_process_sdk",
            "policy_decision": "none", "receipt_type": "protectmcp:lifecycle"}


def _match_request(payload: dict[str, Any], body: dict[str, Any],
                   agent_id: str, action_id: str) -> None:
    expected = {key: body[key] for key in ("action_type", "action_ref", "iteration_id")}
    expected.update(agent_id=agent_id, action_id=action_id, mode="payload",
                    decision="observation", type="protectmcp:lifecycle")
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ValueError("Sign Action returned a receipt for a different request")
    if type(payload.get("v")) is not int or payload["v"] != 1:
        raise ValueError("Sign Action returned an unsupported receipt version")
    context_bytes = canonical(body["context"])
    digest = {"hash": hashlib.sha256(context_bytes).hexdigest(), "size": len(context_bytes)}
    if canonical(payload.get("payload_digest")) != canonical(digest):
        raise ValueError("Sign Action returned a different context digest")
    if payload.get("context") is not None and canonical(payload["context"]) != context_bytes:
        raise ValueError("Sign Action returned a different carried context")


def profile_result(data: dict[str, Any], body: dict[str, Any],
                   agent_id: str, status_code: int) -> dict[str, Any]:
    result = response_payload(data, "Sign Action", (
        ("signature_id", "text"), ("action_id", "text"),
        ("timestamp", "number"), ("verification_url", "text"),
        ("anchor_pending", "flag"), ("decision", "text"),
        ("policy_decision", "text"), ("policy_enforcement", "text_or_null"),
    ))
    payload, signature, anchors = (data.get(key) for key in ("payload", "signature", "anchors"))
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        raise ValueError("Sign Action did not return a profile receipt")
    if not isinstance(anchors, list) or any(not isinstance(item, dict) for item in anchors):
        raise ValueError("Sign Action returned malformed anchors")
    receipt = {"payload": payload, "signature": signature, "anchors": anchors}
    canonical(receipt)
    _match_request(payload, body, agent_id, result["action_id"])
    signature_fields = response_payload(signature, "Sign Action signature", (
        ("alg", "text"), ("kid", "text"), ("sig", "text"),
    ))
    if signature_fields["kid"] != required_text(payload, "issuer_id"):
        raise ValueError("Sign Action returned a mismatched issuer")
    if result["decision"] != "observation" or result["policy_decision"] != "none":
        raise ValueError("Sign Action returned conflicting observation metadata")
    pending = (status_code == 202 or result["anchor_pending"] or not anchors
               or any(item.get("status") == "pending" for item in anchors))
    return {**result, "authorized": False, "anchor_pending": pending,
            "receipt": receipt, "receipt_json": canonical(receipt).decode("utf-8"),
            "action_ref": body["action_ref"], "iteration_id": body["iteration_id"],
            "reason": "observation", "detail": "Receipt saved. This observation does not approve an action."}
