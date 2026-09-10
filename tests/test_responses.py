"""Malformed upstream bodies must stop before any SDK message is emitted."""
import json

import pytest

from tests.test_consumer import PENDING, SIGN, consumer  # noqa: F401

VERIFY = {"verified": True, "signature_id": "sig_fixture", "agent_id": None,
          "agent_name": None, "action_type": None, "algorithm": "ML-DSA-65",
          "signed_at": "2026-09-08T00:00:00Z", "verification_url": "https://example.invalid"}
CASES = [("sign_action", SIGN), ("request_action", PENDING), ("verify_signature", VERIFY)]
PARAMS = {"action_type": "deploy:production", "signature_id": "sig_fixture"}


@pytest.mark.parametrize("tool,body", CASES)
@pytest.mark.parametrize("value", [None, [], [1], "upstream failure", 1, True])
def test_non_object_response_stops(consumer, tool, body, value):
    invoke, requests, reply = consumer
    reply["content"] = json.dumps(value)
    with pytest.raises(ValueError, match="response"):
        invoke(tool, PARAMS)
    assert len(requests) == 1


@pytest.mark.parametrize("tool,body,field", [(tool, body, key) for tool, body in CASES for key in body])
def test_missing_response_field_stops(consumer, tool, body, field):
    invoke, _, reply = consumer
    reply["json"] = {key: value for key, value in body.items() if key != field}
    with pytest.raises(ValueError, match=field):
        invoke(tool, PARAMS)


@pytest.mark.parametrize("tool,body,field", [(tool, body, key) for tool, body in CASES for key, value in body.items()
                                           if isinstance(value, str)])
@pytest.mark.parametrize("value", [None, "", "  ", False, 3, {}, []])
def test_required_text_response_stops(consumer, tool, body, field, value):
    invoke, _, reply = consumer
    reply["json"] = {**body, field: value}
    with pytest.raises(ValueError, match=field):
        invoke(tool, PARAMS)


@pytest.mark.parametrize("value", [None, True, False, "2026-09-08T00:00:00Z", {}, [], float("nan"),
                                 float("inf"), -float("inf"), 10 ** 1000])
def test_sign_timestamp_must_be_finite_number(consumer, value):
    invoke, _, reply = consumer
    reply["content"] = json.dumps({**SIGN, "timestamp": value})
    with pytest.raises(ValueError, match="timestamp"):
        invoke("sign_action", PARAMS)


@pytest.mark.parametrize("value", [0, 1788854400, 1788854400.125])
def test_numeric_timestamp_preserved(consumer, value):
    invoke, _, reply = consumer
    reply["json"] = {**SIGN, "timestamp": value}
    result = invoke("sign_action", PARAMS)
    assert result["authorized"] is True and result["timestamp"] == value


@pytest.mark.parametrize("field", ["approvals_required", "signatures_collected"])
@pytest.mark.parametrize("value", [None, True, False, -1, 1.5, 2.0, "2", {}, [], float("nan"), float("inf"), 10 ** 1000])
def test_session_counts_are_finite_integers(consumer, field, value):
    invoke, _, reply = consumer
    reply["content"] = json.dumps({**PENDING, field: value})
    with pytest.raises(ValueError, match=field):
        invoke("request_action", PARAMS)


def test_session_needs_positive_approval_count(consumer):
    invoke, _, reply = consumer
    reply["json"] = {**PENDING, "approvals_required": 0}
    with pytest.raises(ValueError, match="approvals_required"):
        invoke("request_action", PARAMS)


def test_pending_session_remains_non_authorizing(consumer):
    invoke, requests, reply = consumer
    reply["json"] = {**PENDING, "approvals_required": 1}
    result = invoke("request_action", PARAMS)
    assert result["status"] == "pending" and result["signatures_collected"] == 0
    assert "authorized" not in result and len(requests) == 1


@pytest.mark.parametrize("value", [None, "true", 1, 0, {}, []])
def test_verified_requires_actual_boolean(consumer, value):
    invoke, _, reply = consumer
    reply["json"] = {**VERIFY, "verified": value}
    with pytest.raises(ValueError, match="verified"):
        invoke("verify_signature", PARAMS)


@pytest.mark.parametrize("field", ["agent_id", "agent_name", "action_type"])
@pytest.mark.parametrize("value", [False, 0, {}, []])
def test_redacted_fields_reject_wrong_types(consumer, field, value):
    invoke, _, reply = consumer
    reply["json"] = {**VERIFY, field: value}
    with pytest.raises(ValueError, match=field):
        invoke("verify_signature", PARAMS)


@pytest.mark.parametrize("value", [None, "", "signature-fixture"])
def test_optional_signature_and_redaction_preserved(consumer, value):
    invoke, _, reply = consumer
    reply["json"] = {**SIGN, "signature_b64": value}
    assert invoke("sign_action", PARAMS)["signature_b64"] == value
    reply["json"] = VERIFY
    result = invoke("verify_signature", PARAMS)
    assert all(result[field] is None for field in ["agent_id", "agent_name", "action_type"])


@pytest.mark.parametrize("value", [False, 3, [], {}])
def test_optional_signature_rejects_wrong_types(consumer, value):
    invoke, _, reply = consumer
    reply["json"] = {**SIGN, "signature_b64": value}
    with pytest.raises(ValueError, match="signature_b64"):
        invoke("sign_action", PARAMS)


@pytest.mark.parametrize("field,value", [("error", {}), ("attestation_hash", []),
                                       ("denial_signature_id", False), ("signed_deny", [])])
def test_malformed_denial_cannot_emit_wrong_selector_types(consumer, field, value):
    invoke, _, reply = consumer
    reply.update(status=403, json={"detail": {"error": "action_denied", field: value}})
    with pytest.raises(ValueError):
        invoke("sign_action", PARAMS)


@pytest.mark.parametrize("tool,body", CASES)
def test_non_json_response_stops(consumer, tool, body):
    invoke, _, reply = consumer
    reply["content"] = "<html>upstream failure</html>"
    with pytest.raises(ValueError):
        invoke(tool, PARAMS)


def test_negative_hosted_verdict_is_preserved(consumer):
    invoke, _, reply = consumer
    reply["json"] = {**VERIFY, "verified": False}
    assert invoke("verify_signature", PARAMS)["verified"] is False


def test_unknown_response_field_kind_is_rejected():
    from tools._responses import response_payload

    with pytest.raises(ValueError, match="Unknown response field kind"):
        response_payload({"timestamp": 1}, "fixture", [("timestamp", "present")])
