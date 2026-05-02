<p align="center">
  <a href="https://asqav.com"><img src="https://asqav.com/logo-text-white.png" alt="Asqav" width="150"></a>
</p>

# Asqav Dify Plugin

Post-quantum agent signing and verification for Dify workflows.

## What it does

This plugin connects Dify workflows to the [Asqav](https://asqav.com) API, adding ML-DSA-65 post-quantum cryptographic signing to agent actions. Every signed action creates an audit record that anyone can verify.

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
Signs an agent action with ML-DSA-65. Provide an action type (e.g. "read:data", "tool:execute") and optional context. Returns a signature ID and public verification URL.

### Verify Signature
Verifies a signature by its ID. This is a public endpoint - no authentication needed. Returns the verification status, signing agent, action details, and timestamp.

### Request Action
Creates a multi-party signing session for high-risk actions. The action must be approved by enough signing entities before it is authorized. Use this as a pre-execution gate in workflows.

## Setup

1. Get an API key at [asqav.com](https://asqav.com)
2. Create an agent via the Asqav dashboard or SDK
3. Enter your API key and Agent ID in the plugin credentials

## Credentials

- **asqav API Key**: Your API key from asqav.com (starts with `sk_`)
- **Agent ID**: The agent to use for signing (starts with `agent_`)

## Links

- [asqav documentation](https://asqav.com/docs)
- [asqav SDK on PyPI](https://pypi.org/project/asqav/)
- [Source code](https://github.com/jagmarques/dify-plugin-asqav)

## Contact

Author: asqav (https://asqav.com)
