# Asqav Dify Plugin

Use Asqav tools at selected points in a Dify workflow to sign an action, query a signature, or create an approval session. You choose which actions reach these tools and how the workflow responds.

## Configuration

1. Sign up at [asqav.com](https://asqav.com) and create an API key beginning with `sk_`.
2. Create an agent through the Asqav dashboard or SDK. Copy its ID, which begins with `agt_`.
3. In Dify, open Plugins, select Asqav, and enter the API key and Agent ID. Credential validation checks that the key can access the agent.

Request Action also needs an active signing group configured for that agent and an account with approval quorum access. An agent ID alone does not configure approvers.

## Sign Action

Send an `action_type`, such as `read:data` or `tool:execute`, and optional `context`. The context must be a JSON object encoded as a string. Plain text is sent as `{"raw": "your text"}`; JSON arrays and scalar values are rejected.

A successful sign returns `authorized: true`, identifiers, timestamp, signature, and a verification URL. A refused sign returns `authorized: false` with a reason. Asqav may include a `signed_deny` envelope or a `denial_signature_id`; either can be absent. Halt, delegation, quarantine, and other refusals do not always carry a signed denial.

For a step with a side effect:

1. Place Sign Action immediately before the step.
2. Add an IF/ELSE branch that continues only when `authorized` equals `true`.
3. Route `false` and tool errors to a stop or review path. Do not connect an error fallback to the protected step.

The tool does not execute or intercept other nodes. A signature records the submitted action; it does not prove that a later step ran. Passing the same optional `action_ref` before and after a step links those receipts without proving execution.

## Verify Signature

Pass a `signature_id` to query Asqav's hosted verification endpoint. The response includes the verification result and available action details. Private receipt fields can be null.

The outbound verification request sends no API key. Dify still requires the provider's API key and Agent ID during plugin setup. This tool uses the hosted service; it does not perform offline signature verification.

## Request Action

Provide an `action_type` and optional `params`, with the same JSON-object or plain-text format as Sign Action context. The tool creates an approval session and returns its ID, status, approval counts, and expiry immediately.

Request Action has no `authorized` output and does not wait for approvals. To protect a later step, keep the workflow stopped while the session is pending. Collect approvals through Asqav and query the session through the Asqav API. Continue only after checking that the matching session is approved and unexpired. Treat expired, rejected, missing, and failed checks as a stop. Session approval and execution of your workflow step are separate operations.

The plugin exposes session creation. Approval collection and status polling require separate API calls or workflow logic. See [Asqav documentation](https://asqav.com/docs) for the signing-group API.

## Agent apps

Adding these tools makes them available to the agent. Coverage depends on whether the agent calls them; it does not automatically capture every action. Use explicit workflow nodes and branches when a step must require authorization.

## Data handling

Sign Action sends the complete supplied context to `api.asqav.com`, and Request Action sends the complete supplied parameters. This plugin does not hash payloads locally. Omit sensitive data you do not want sent to Asqav. Running the Python SDK separately does not change this plugin's request path.

Asqav's service processes those requests under its [privacy policy](https://asqav.com/privacy). The plugin does not write payloads to its own local storage; Dify manages credentials, workflow inputs, outputs, and any execution logs under your deployment's settings. See [PRIVACY.md](PRIVACY.md) for the transmitted fields.

## Development

The runner uses Python 3.12. Install the runtime and test dependencies, then run the tests:

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

The consumer tests load the plugin through the Dify SDK and use HTTP fixtures. They do not establish a live service result or a complete Dify workflow run.

Package with the Dify Plugin CLI and check the archive before distribution:

```sh
dify plugin package . -o asqav.difypkg
python scripts/check_package.py asqav.difypkg
```

## License and contact

The plugin is source-available under the [Elastic License 2.0](LICENSE). The complete license terms are included in the package.

[Plugin source](https://github.com/jagmarques/dify-plugin-asqav) · [Python SDK](https://pypi.org/project/asqav/) · [Documentation](https://asqav.com/docs)

Contact: info@asqav.com
