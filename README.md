<p align="center">
  <a href="https://asqav.com"><img src="https://asqav.com/logo-text-white.png" alt="asqav" width="150"></a>
</p>

# asqav Dify Plugin

Post-quantum agent signing and verification for Dify workflows.

## What it does

This plugin connects Dify workflows to the [asqav](https://asqav.com) API, adding ML-DSA-65 post-quantum cryptographic signing to agent actions. Every signed action creates a tamper-evident audit record that anyone can verify.

## Tools

### Sign Action
Signs an agent action with ML-DSA-65. Provide an action type (e.g. "read:data", "tool:execute") and optional context. Returns a signature ID and public verification URL.

### Verify Signature
Verifies a signature by its ID. This is a public endpoint - no authentication needed. Returns the verification status, signing agent, action details, and timestamp.

### Request Action
Creates a multi-party signing session for high-risk actions. The action must be approved by enough signing entities before it is authorized. Use this as a pre-execution gate in workflows.

## Setup

1. Get an API key at [asqav.com](https://asqav.com)
2. Create an agent via the asqav dashboard or SDK
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
