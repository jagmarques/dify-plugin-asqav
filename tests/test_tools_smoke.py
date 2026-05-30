"""Smoke tests for the Asqav Dify plugin tools.

These tests instantiate the tool classes without the full Dify session because
booting a real Session requires a Dify host. Instead, we build a minimal
runtime stub directly and exercise each tool's `_invoke` generator with a
mocked HTTP layer.
"""

from __future__ import annotations

from typing import Any

import pytest
from dify_plugin.entities.tool import ToolInvokeMessage, ToolRuntime

from tools.request_action import RequestActionTool
from tools.sign_action import SignActionTool, _denied_result
from tools.verify_signature import VerifySignatureTool


def _make_tool(tool_cls, credentials: dict[str, Any]):
    """Build a tool instance without going through Dify Session machinery."""
    tool = object.__new__(tool_cls)
    tool.runtime = ToolRuntime(
        credentials=credentials,
        user_id=None,
        session_id=None,
    )
    tool.session = None
    tool.response_type = ToolInvokeMessage
    return tool


@pytest.fixture
def credentials() -> dict[str, Any]:
    return {
        "asqav_api_key": "sk_test_1234567890abcdef",
        "asqav_agent_id": "agent_test_abc123",
    }


def test_tool_modules_import() -> None:
    """All three tool modules import cleanly and expose their classes."""
    from tools import request_action, sign_action, verify_signature

    assert hasattr(sign_action, "SignActionTool")
    assert hasattr(verify_signature, "VerifySignatureTool")
    assert hasattr(request_action, "RequestActionTool")


def test_sign_action_posts_expected_body(
    mocker, credentials: dict[str, Any], fake_response_factory
) -> None:
    """SignActionTool posts to /agents/{agent_id}/sign with the action_type
    and parsed context payload."""
    fake_post = mocker.patch(
        "tools.sign_action.httpx.post",
        return_value=fake_response_factory(
            status_code=200,
            json_data={
                "signature_id": "sig_123",
                "action_id": "act_456",
                "timestamp": "2026-05-23T00:00:00Z",
                "verification_url": "https://api.asqav.com/api/v1/verify/sig_123",
            },
        ),
    )

    tool = _make_tool(SignActionTool, credentials)
    messages = list(
        tool._invoke({"action_type": "tool:execute", "context": '{"foo": "bar"}'})
    )

    fake_post.assert_called_once()
    _, kwargs = fake_post.call_args
    assert kwargs["headers"]["X-API-Key"] == credentials["asqav_api_key"]
    assert kwargs["json"]["action_type"] == "tool:execute"
    assert kwargs["json"]["context"] == {"foo": "bar"}

    assert len(messages) == 1


def test_sign_action_treats_invalid_json_context_as_raw(
    mocker, credentials: dict[str, Any], fake_response_factory
) -> None:
    """When the user-provided context is not JSON, the tool falls back to a
    {raw: ...} wrapper rather than raising."""
    fake_post = mocker.patch(
        "tools.sign_action.httpx.post",
        return_value=fake_response_factory(
            status_code=200,
            json_data={
                "signature_id": "sig_x",
                "action_id": "act_x",
                "timestamp": "2026-05-23T00:00:00Z",
                "verification_url": "https://api.asqav.com/api/v1/verify/sig_x",
            },
        ),
    )

    tool = _make_tool(SignActionTool, credentials)
    list(tool._invoke({"action_type": "read:data", "context": "not-json"}))

    _, kwargs = fake_post.call_args
    assert kwargs["json"]["context"] == {"raw": "not-json"}


def test_verify_signature_calls_public_endpoint(
    mocker, credentials: dict[str, Any], fake_response_factory
) -> None:
    """VerifySignatureTool hits the unauthenticated /verify/{id} endpoint."""
    fake_get = mocker.patch(
        "tools.verify_signature.httpx.get",
        return_value=fake_response_factory(
            status_code=200,
            json_data={
                "verified": True,
                "signature_id": "sig_123",
                "agent_id": "agent_test_abc123",
                "agent_name": "test-agent",
                "action_type": "tool:execute",
                "algorithm": "ML-DSA-65",
                "signed_at": "2026-05-23T00:00:00Z",
                "verification_url": "https://api.asqav.com/api/v1/verify/sig_123",
            },
        ),
    )

    tool = _make_tool(VerifySignatureTool, credentials)
    messages = list(tool._invoke({"signature_id": "sig_123"}))

    fake_get.assert_called_once()
    args, _ = fake_get.call_args
    assert args[0].endswith("/verify/sig_123")
    assert len(messages) == 1


def test_request_action_builds_signing_session_body(
    mocker, credentials: dict[str, Any], fake_response_factory
) -> None:
    """RequestActionTool posts to /signing-groups/sessions with agent_id +
    action_type and yields one JSON message."""
    fake_post = mocker.patch(
        "tools.request_action.httpx.post",
        return_value=fake_response_factory(
            status_code=200,
            json_data={
                "session_id": "ses_1",
                "status": "pending",
                "approvals_required": 2,
                "signatures_collected": 0,
                "action_type": "transfer:funds",
                "created_at": "2026-05-23T00:00:00Z",
                "expires_at": "2026-05-23T01:00:00Z",
            },
        ),
    )

    tool = _make_tool(RequestActionTool, credentials)
    messages = list(
        tool._invoke({"action_type": "transfer:funds", "params": '{"amount": 100}'})
    )

    fake_post.assert_called_once()
    args, kwargs = fake_post.call_args
    assert args[0].endswith("/signing-groups/sessions")
    assert kwargs["json"]["agent_id"] == credentials["asqav_agent_id"]
    assert kwargs["json"]["action_type"] == "transfer:funds"
    assert kwargs["json"]["params"] == {"amount": 100}
    assert len(messages) == 1


def test_sign_action_surfaces_403_without_raising(
    mocker, credentials: dict[str, Any], fake_response_factory
) -> None:
    """A 403 policy decision is yielded as one structured message, never raised."""
    mocker.patch(
        "tools.sign_action.httpx.post",
        return_value=fake_response_factory(
            status_code=403,
            json_data={
                "detail": "Organization is under emergency halt; signing is disabled"
            },
        ),
    )

    tool = _make_tool(SignActionTool, credentials)
    messages = list(tool._invoke({"action_type": "refund:approve", "context": ""}))

    assert len(messages) == 1


@pytest.mark.parametrize(
    ("detail", "expected_reason"),
    [
        ("Organization is under emergency halt; signing is disabled", "emergency_halt"),
        ("Action type is outside the agent's delegated scope", "delegation_denied"),
        ("Agent's delegation has expired", "delegation_denied"),
        ("Agent is in quarantine mode (read/verify only, signing disabled)", "quarantine"),
        ("Some unmapped refusal text", "denied"),
    ],
)
def test_denied_result_maps_string_details(
    detail: str, expected_reason: str, fake_response_factory
) -> None:
    """String-form 403 details map to a stable machine reason."""
    result = _denied_result(fake_response_factory(status_code=403, json_data={"detail": detail}))

    assert result["authorized"] is False
    assert result["reason"] == expected_reason
    assert result["detail"] == detail
    assert result["signed_deny"] is None


def test_denied_result_passes_through_signed_deny_envelope(fake_response_factory) -> None:
    """A policy/content block returns policy_blocked with its signed denial receipt."""
    detail = {
        "error": "action_denied",
        "attestation_hash": "abc123",
        "signed_deny": {"body": {}, "signature_b64": "ZmFrZQ==", "algorithm": "ML-DSA-65"},
    }
    result = _denied_result(fake_response_factory(status_code=403, json_data={"detail": detail}))

    assert result["authorized"] is False
    assert result["reason"] == "policy_blocked"
    assert result["attestation_hash"] == "abc123"
    assert result["signed_deny"]["signature_b64"] == "ZmFrZQ=="
