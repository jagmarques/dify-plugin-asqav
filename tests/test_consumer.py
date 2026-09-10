"""Load the real Dify SDK registry and executor with non-delegating HTTP fixtures."""
from pathlib import Path
import json

import httpx
import pytest
from dify_plugin import DifyPluginEnv
from dify_plugin.core.entities.plugin.request import ToolInvokeRequest
from dify_plugin.core.plugin_executor import PluginExecutor
from dify_plugin.core.plugin_registration import PluginRegistration
from dify_plugin.core.runtime import Session
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from provider.asqav import AsqavProvider

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = {"asqav_api_key": "sk_fixture", "asqav_agent_id": "agt_fixture"}
SIGN = {"signature_id": "sig_fixture", "action_id": "act_fixture", "timestamp": 1788854400,
        "verification_url": "https://example.invalid/sig_fixture"}
PENDING = {"session_id": "thr_fixture", "status": "pending", "approvals_required": 2,
           "signatures_collected": 0, "action_type": "deploy:production",
           "created_at": "2026-09-08T00:00:00Z", "expires_at": "2026-09-09T00:00:00Z"}


@pytest.fixture
def consumer(monkeypatch):
    monkeypatch.chdir(ROOT)
    config = DifyPluginEnv()
    registry = PluginRegistration(config)
    assert set(registry.tools_mapping["asqav"][2]) == {"sign_action", "request_action", "verify_signature"}
    executor = PluginExecutor(config, registry)
    session = Session.empty_session()
    requests = []
    reply = {"status": 200, "json": SIGN}

    def respond(request):
        requests.append(request)
        if "content" in reply:
            return httpx.Response(reply["status"], content=reply["content"])
        return httpx.Response(reply["status"], json=reply["json"])

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(httpx, "post", client.post)
        monkeypatch.setattr(httpx, "get", client.get)

        def invoke(tool, params, credentials=CREDENTIALS):
            request = ToolInvokeRequest(provider="asqav", tool=tool, tool_parameters=params,
                                        credentials=credentials, user_id="fixture")
            messages = list(executor.invoke_tool(session, request))
            payload = next(m.message.json_object for m in messages if m.type == ToolInvokeMessage.MessageType.JSON)
            variables = {m.message.variable_name: m.message.variable_value for m in messages
                         if m.type == ToolInvokeMessage.MessageType.VARIABLE}
            assert payload == variables
            return payload

        yield invoke, requests, reply
    session._executor.shutdown(wait=True)


@pytest.mark.parametrize("tool,field", [("sign_action", "context"), ("request_action", "params")])
@pytest.mark.parametrize("value", ["[]", "null", "42", '"scalar"', "false", [], 4, False])
def test_non_object_input_stops_before_http(consumer, tool, field, value):
    invoke, requests, _ = consumer
    with pytest.raises(ValueError, match=field):
        invoke(tool, {"action_type": "tool:execute", field: value})
    assert requests == []


@pytest.mark.parametrize("tool", ["sign_action", "request_action"])
@pytest.mark.parametrize("value", [None, "", "  ", [], 3, False])
def test_action_type_stops_before_http(consumer, tool, value):
    invoke, requests, _ = consumer
    with pytest.raises(ValueError, match="action_type"):
        invoke(tool, {"action_type": value})
    assert requests == []


@pytest.mark.parametrize("tool,field,wire", [("sign_action", "context", "context"), ("request_action", "params", "params")])
@pytest.mark.parametrize("value,expected", [('{}', {}), ('{"email":"person@example.invalid"}', {"email": "person@example.invalid"}), ("plain text", {"raw": "plain text"})])
def test_complete_input_transmission(consumer, tool, field, wire, value, expected):
    invoke, requests, reply = consumer
    reply["json"] = SIGN if tool == "sign_action" else PENDING
    result = invoke(tool, {"action_type": "tool:execute", field: value})
    assert json.loads(requests[0].content)[wire] == expected
    assert requests[0].headers["X-API-Key"] == CREDENTIALS["asqav_api_key"]
    if tool == "request_action":
        assert result["status"] == "pending" and "authorized" not in result
        assert len(requests) == 1


@pytest.mark.parametrize("identifier", ["../agents", "agt_a/sign?x=y", "agt_a#b", "agt_%2f", " ", None, 3])
@pytest.mark.parametrize("tool", ["sign_action", "request_action", "verify_signature"])
def test_identifiers_cannot_change_endpoint(consumer, identifier, tool):
    invoke, requests, _ = consumer
    with pytest.raises(ValueError):
        invoke(tool, {"action_type": "tool:execute", "signature_id": identifier},
               {**CREDENTIALS, "asqav_agent_id": identifier})
    assert requests == []


@pytest.mark.parametrize("credentials", [{}, {**CREDENTIALS, "asqav_api_key": " "}, {**CREDENTIALS, "asqav_agent_id": "../x"}])
def test_provider_invalid_input_stops_before_http(consumer, credentials):
    _, requests, _ = consumer
    with pytest.raises(ToolProviderCredentialValidationError):
        AsqavProvider().validate_credentials(credentials)
    assert requests == []


@pytest.mark.parametrize("detail", [None, [], "", "Unknown refusal", {"error": "scope_missing"}, {"error": "action_denied", "denial_signature_id": "sig_denial", "signed_deny": None}])
def test_refusals_remain_false_and_nullable(consumer, detail):
    invoke, _, reply = consumer
    reply.update(status=403, json={"detail": detail})
    result = invoke("sign_action", {"action_type": "tool:execute"})
    assert result["authorized"] is False and result["signed_deny"] is None
    assert result["denial_signature_id"] == (detail.get("denial_signature_id") if isinstance(detail, dict) else None)


def test_malformed_refusal_is_not_authorization(consumer):
    invoke, _, reply = consumer
    reply.update(status=403, json=[])
    assert invoke("sign_action", {"action_type": "tool:execute"})["authorized"] is False


@pytest.mark.parametrize("status", [401, 422, 429, 500])
def test_non_policy_errors_remain_errors(consumer, status):
    invoke, requests, reply = consumer
    reply.update(status=status, json={"detail": "fixture error"})
    with pytest.raises(httpx.HTTPStatusError):
        invoke("sign_action", {"action_type": "tool:execute"})
    assert len(requests) == 1


def test_verify_is_hosted_and_needs_no_outbound_credentials(consumer):
    invoke, requests, reply = consumer
    reply["json"] = {"verified": True, "signature_id": "sig_fixture", "agent_id": None,
                     "agent_name": None, "action_type": None, "algorithm": "ML-DSA-65",
                     "signed_at": "2026-09-08T00:00:00Z", "verification_url": "https://example.invalid"}
    result = invoke("verify_signature", {"signature_id": "sig_fixture"}, {})
    assert result["verified"] is True and result["agent_id"] is None
    assert "x-api-key" not in requests[0].headers


@pytest.mark.parametrize("value", [" ", 0, False, [], 3])
def test_optional_action_reference_validation(consumer, value):
    invoke, requests, _ = consumer
    with pytest.raises(ValueError, match="action_ref"):
        invoke("sign_action", {"action_type": "tool:execute", "action_ref": value})
    assert requests == []
