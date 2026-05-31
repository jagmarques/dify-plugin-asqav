<p align="center">
  <a href="https://asqav.com"><img src="https://asqav.com/logo-text-white.png" alt="Asqav" width="150"></a>
</p>

# Asqav Dify Plugin

Stop a rogue agent before it acts, and prove what it tried. For Dify workflows.

## What it does

This plugin sends each agent action to the [Asqav](https://asqav.com) API before your workflow commits to it. Asqav checks the action against your policies: a blocked action comes back rejected with a forensic record of the attempt, and an allowed action proceeds and is signed with ML-DSA-65 into a verifiable audit trail. Either way you get tamper-evident evidence of what the agent tried.

## Data handling

This plugin calls the Asqav cloud API (`https://api.asqav.com`) directly from your Dify deployment. Action context (`action_type` and any `context` JSON you pass) is transmitted to the cloud where it is signed with ML-DSA-65. The cloud applies GDPR-aware data minimization: only the metadata bag (action_type, agent_id, session_id, model_name, tool_name) is retained alongside a hash of the rest where possible.

If you need client-side hash-only behavior, use the `asqav` Python SDK directly in your Dify workflow alongside this plugin:

```python
import asqav

asqav.init(api_key="sk_...", base_url="https://api.asqav.com", mode="hash-only")
```

The plugin inherits the SDK's `mode` behavior whenever it is invoked through the SDK rather than directly. See [docs/fingerprint-spec.md](https://github.com/jagmarques/asqav-sdk/blob/main/docs/fingerprint-spec.md) in the SDK repo for the fingerprint spec and conformance vectors.

## Tools

### Sign Action
Signs an agent action with ML-DSA-65. Provide an action type (e.g. "read:data", "tool:execute") and optional context JSON.

Returns a JSON object with an `authorized` boolean so a workflow can branch on the decision instead of failing:

- When the action is permitted, `authorized` is `true` and the result includes `signature_id`, `action_id`, `timestamp`, `verification_url`, and the base64 ML-DSA-65 signature in `signature_b64`.
- When the action is blocked, `authorized` is `false` and the result includes a machine `reason` (`policy_blocked`, `emergency_halt`, `delegation_denied`, `quarantine`, or `denied`) plus a human-readable `detail`. A policy block also returns `attestation_hash` and a `signed_deny` envelope, which is itself a verifiable signed denial receipt.

### Verify Signature
Verifies a signature by its ID. This is a public endpoint - no authentication needed. Returns `verified`, the signing `agent_id` and `agent_name`, the `action_type`, the `algorithm` (e.g. ML-DSA-65), the `signed_at` timestamp, and the `verification_url`.

### Request Action
Creates a multi-party signing session for high-risk actions. The action must be approved by enough signing entities before it is authorized. Use this as a pre-execution gate in workflows. Returns the `session_id`, `status`, `approvals_required`, `signatures_collected`, `action_type`, `created_at`, and `expires_at`.

## Setup

1. Get an API key at [asqav.com](https://asqav.com)
2. Create an agent via the Asqav dashboard or SDK
3. Enter your API key and Agent ID in the plugin credentials

## Credentials

- **Asqav API Key**: Your API key from asqav.com (starts with `sk_`)
- **Agent ID**: The agent to use for signing (starts with `agent_`)

## Development

Run the smoke test suite locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

The suite covers the provider entrypoint and each tool. Network calls to the
Asqav API are mocked, so the tests run offline. CI runs the same suite on
Python 3.12 (matching the plugin runner version in `manifest.yaml`) for every
PR and push to `main`.

## Links

- [Asqav documentation](https://asqav.com/docs)
- [Asqav SDK on PyPI](https://pypi.org/project/asqav/)
- [Source code](https://github.com/jagmarques/dify-plugin-asqav)

## Contact

Author: Asqav (https://asqav.com)
