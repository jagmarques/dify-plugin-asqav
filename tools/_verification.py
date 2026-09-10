"""Expose hosted evidence without treating its signature rollup as a profile pass."""
import hashlib
from typing import Any

from tools._responses import response_payload
from tools._profile import canonical

_BOOLEAN_AXES = (
    "signature_valid", "signer_key_match", "algorithm_match", "agent_active",
    "chain_valid", "anchor_valid_ots", "anchor_valid_rfc3161",
    "policy_digest_resolved", "duplicate_emission_candidate",
    "counterparty_binding_verified", "keyed_digest_verified",
)


def hosted_evidence(data: dict[str, Any]) -> dict[str, Any]:
    detail = data.get("verification_detail")
    if detail is None:
        return {"profile_verdict": "unverified", "profile_failure_class": "unverifiable",
                "profile_check_limit": "Hosted verification details are unavailable."}
    if not isinstance(detail, dict):
        raise ValueError("Verify Signature returned malformed verification details")
    for key in _BOOLEAN_AXES:
        value = detail.get(key)
        if value is not None and type(value) is not bool:
            raise ValueError("Verify Signature returned a malformed verification axis")
    if detail.get("failure_class") not in (None, "invalid", "unverifiable"):
        raise ValueError("Verify Signature returned an unknown failure class")
    fields = response_payload(data, "Verify Signature", (
        ("anchor_confirmed", "flag"),
        ("execution_evidence", "object_or_null"),
    ))
    stale = data.get("stale_pending")
    if stale is not None and type(stale) is not bool:
        raise ValueError("Verify Signature returned malformed anchor freshness")
    return {**fields, "verification_detail": detail,
            "signature_valid": detail.get("signature_valid"), "stale_pending": stale,
            "profile_verdict": "unverified",
            "profile_failure_class": _profile_failure(detail),
            "profile_check_limit": "Hosted ID lookup does not verify an exact supplied receipt, its key thumbprint or sequence continuity."}


def _profile_failure(detail: dict[str, Any]) -> str:
    failed = ("signature_valid",)
    if detail.get("failure_class") == "invalid" or any(detail.get(key) is False for key in failed):
        return "invalid"
    return "unverifiable"


_REQUIRED_CHECKS = {
    "structure", "receipt_binding", "identity", "key_thumbprint", "revocation", "issuer",
    "signature", "stored_mirrors", "chain", "sequence", "context_digest", "action_ref",
    "future_skew", "policy_digest", "anchors", "witness_quorum",
}
_MUST_PASS = {"structure", "receipt_binding", "identity", "revocation", "issuer", "signature",
              "stored_mirrors", "chain", "future_skew", "policy_digest", "anchors"}


def _bound_detail(data: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    detail = data.get("profile_verification")
    if not isinstance(detail, dict):
        raise ValueError("Verify Signature did not return exact-receipt verification")
    expected_digest = "sha256:" + hashlib.sha256(canonical(receipt)).hexdigest()
    if detail.get("receipt_digest") != expected_digest:
        raise ValueError("Verify Signature returned a result for a different receipt")
    checks = detail.get("checks")
    if not isinstance(checks, dict) or any(v not in ("pass", "invalid", "unverifiable", "not_applicable") for v in checks.values()):
        raise ValueError("Verify Signature returned malformed profile checks")
    for key in ("expired", "anchor_valid_ots", "anchor_valid_rfc3161"):
        if detail.get(key) is not None and type(detail[key]) is not bool:
            raise ValueError("Verify Signature returned a malformed profile flag")
    if type(detail.get("duplicate_emission_candidate")) is not bool:
        raise ValueError("Verify Signature returned a malformed duplicate flag")
    return detail


def _required_pass(receipt: dict[str, Any], context_supplied: bool) -> set[str]:
    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("receipt_json must contain a payload object")
    required = _MUST_PASS | ({"context_digest", "action_ref"}
                            if context_supplied or payload.get("context") is not None else set())
    if "key_thumbprint" in payload:
        required |= {"key_thumbprint"}
    return required | {k for k in ("counterparty_binding", "authorized_under_mandate", "result_digest") if k in payload}


def _bound_verdict(data: dict[str, Any], detail: dict[str, Any], required: set[str]) -> bool:
    verdict, failure, checks = detail.get("verdict"), detail.get("failure_class"), detail["checks"]
    passing = verdict == "verified"
    if passing and (not _REQUIRED_CHECKS <= checks.keys()
                    or any(checks.get(k) != "pass" for k in required)
                    or any(v in ("invalid", "unverifiable") for v in checks.values())
                    or not any(detail.get(k) is True for k in ("anchor_valid_ots", "anchor_valid_rfc3161"))):
        raise ValueError("Verify Signature claimed a pass with incomplete profile checks")
    expected = "pass" if passing else "fail" if failure == "invalid" else "incomplete"
    if (verdict not in ("verified", "unverified") or failure not in (None, "invalid", "unverifiable")
            or passing != (failure is None) or data.get("verdict") != expected
            or data.get("wire_verdict") != verdict or data.get("failure_class") != failure
            or data.get("format") != "asqav-native"):
        raise ValueError("Verify Signature returned conflicting profile verdicts")
    if type(data.get("signature_valid")) is not bool or data["signature_valid"] != (checks.get("signature") == "pass"):
        raise ValueError("Verify Signature returned a conflicting signature check")
    return passing


def bound_evidence(data: dict[str, Any], receipt: dict[str, Any], context_supplied: bool) -> dict[str, Any]:
    detail = _bound_detail(data, receipt)
    passing = _bound_verdict(data, detail, _required_pass(receipt, context_supplied))
    checks = detail["checks"]
    return {"verified": passing, "authorized": False, "signature_valid": data["signature_valid"],
            "profile_verdict": detail["verdict"], "profile_failure_class": detail["failure_class"],
            "profile_verification": detail, "expired": detail.get("expired"),
            "anchor_confirmed": checks.get("anchors") == "pass",
            "profile_check_limit": ", ".join(k for k, v in checks.items() if v == "unverifiable")}
