# Asqav Dify Plugin

Save signed records of selected workflow actions in [Asqav](https://www.asqav.com/) and check them later. Connect with your Asqav API key and agent ID. You choose which actions are recorded.

## Configuration

1. [Create an Asqav account](https://www.asqav.com/signup) or [sign in](https://www.asqav.com/login). For email registration, verify your email before creating an API key.
2. Open [Settings > API](https://www.asqav.com/dashboard/#/settings/api) and create a key with the permissions below. Copy the full key once into a secret store; it begins with `sk_`. Do not put it in workflow text, exported examples, screenshots or support messages.
3. Create an agent with the [SDK or API](https://www.asqav.com/docs/agents) in the same organization as the key. Copy the returned `agent_id`, beginning with `agt_`. The dashboard's [Agents page](https://www.asqav.com/dashboard/#/agents) lists agents; use the SDK or API to create one.
4. In Dify Cloud, open Integrations → Tools, select Asqav and enter the key and Agent ID. Provider validation checks that the key can read that agent. It does not prove the key can sign or create approval sessions.
5. Try Start → Sign Action → Verify Signature → End with a harmless action such as `read:data`. Map Sign Action’s `signature_id` into Verify Signature. Keep the first example free of side effects. Choose a receipt mode as described below.
6. Review account usage under [Settings > Billing](https://www.asqav.com/dashboard/#/settings/billing). See [current plans](https://www.asqav.com/pricing) for limits. The [Change Plan](https://www.asqav.com/dashboard/?action=change-plan) flow directs you to contact Asqav; contact info@asqav.com about an upgrade.

| Operation | API key permission |
| --- | --- |
| Validate the provider and read the agent | `agents:read` |
| Create an agent or use Sign Action | `agents:write` |
| Use Request Action | `signing-groups:write` |
| Query an approval session through the API | `signing-groups:read` |

Default keys include the agent read/write permissions. The dashboard key dialog does not expose signing-group permissions; contact Asqav for help obtaining a key with those scopes. `sessions:read` and `sessions:write` refer to a different API resource.

For API-based agent creation, set `ASQAV_API_KEY` securely in your shell, then run:

```sh
curl --fail-with-body https://api.asqav.com/api/v1/agents/create \
  -H "X-API-Key: $ASQAV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"dify-workflow"}'
```

This creates an agent in your account. Copy only its returned ID into Dify's Agent ID field. Request Action also needs Enterprise approval quorum access and an active signing group for that agent. Configure its approvers under [Multi-party signing](https://www.asqav.com/dashboard/#/signing); an agent ID alone does not configure approvers.

| Setup problem | Next step |
| --- | --- |
| Key creation does not complete | Verify your email and sign in again. Contact info@asqav.com if the form still fails. |
| Invalid API key | Check the full key and whether it has been revoked. Replace it securely if needed. |
| Agent not found or access denied | Check the copied ID, organization and required scopes. |
| Request Action reports no active group or unavailable feature | Check the agent's group and Enterprise quorum access. |
| Timeout or service error | Keep the protected step stopped; investigate the failure before retrying. |

## Sign Action

Send an `action_type`, such as `read:data` or `tool:execute`, and optional `context`. The context must be a JSON object encoded as a string. Plain text is sent as `{"raw": "your text"}`; JSON arrays and scalar values are rejected.

In **Standard** mode (the default for existing nodes), a successful sign returns `authorized: true` with the signature and action IDs. This means the sign endpoint accepted the request; it does not prove that a policy was evaluated. Its timestamp is a finite Unix epoch number in seconds, and it includes a verification URL. Signature bytes may be null. A refused sign returns `authorized: false` with a reason. Asqav may include a `signed_deny` envelope or a `denial_signature_id`; either can be absent. A refusal caused by a halt or delegation may lack a signed denial. The same applies to quarantine and other refusals.

Malformed successful responses, including missing fields or invalid types, raise a tool error. Such errors do not emit an authorization result. JSON output and the named output variables carry the same validated values, including nulls.

For a Standard-mode step with a side effect:

1. Place Sign Action immediately before the step.
2. Add an IF/ELSE branch that continues only when `authorized` equals `true`.
3. Route `false` and tool errors to a stop or review path. Do not connect an error fallback to the protected step.

The tool does not execute or intercept other nodes. A signature records the submitted action; it does not prove that a later step ran. Standard mode accepts an optional reference. In Profile mode, the action reference is derived from the exact action and context; different actions usually have different references. Use one `iteration_id` to correlate steps in the same logical run. Neither field proves execution or prevents replay.

### Profile observations

Choose **Profile observation** to request a Compliance Receipt from Asqav. Supply a unique workflow run ID as `iteration_id`, and reuse it only for steps belonging to that same logical run. Context must be a JSON object: duplicate members, floating-point numbers, invalid Unicode and integers outside the safe JSON range are rejected before signing.

The tool derives `action_ref` using RFC 8785 canonicalization, checks that the response refers to the requested action, agent and run, and retains the exact `payload`, `signature` and `anchors` as `receipt`. `receipt_json` is its canonical JSON serialization. Save that original: the public verification view may redact fields and cannot replace it.

Dify explicitly reports in-process capture and requests an **observation**. A saved observation always returns `authorized: false`; it does not approve another node. `anchor_pending: true` means anchoring is unfinished. Retain the receipt and recheck the same signature ID later rather than signing again. Free includes Bitcoin anchoring, which can be pending after signing. Feature restrictions or unavailable anchoring can still produce a tool error; the plugin never falls back silently to Standard mode.

## Verify Signature

Pass a `signature_id` to query Asqav's hosted verification endpoint. The response includes the verification result and available action details. Private receipt fields can be null.

The outbound verification request sends no API key. Dify still requires the provider's API key and Agent ID during plugin setup. With only an ID, this is a hosted check: `verified` is the service's signature rollup, not an exact-receipt profile result. Neither mode approves execution.

For **Profile observation**, also map Sign Action’s `receipt_json` into Verify Signature. To recheck the action and context, map the same original context into `context_json`. The tool sends the original receipt and optional context to Asqav's shared verifier. It checks the retained signature and key, issuer, signed bytes, chain, sequence when present in adjacent profile receipts, policy digest, timestamps and applicable key thumbprint. It verifies carried timestamp proofs against the exact payload and signature. `profile_verification.checks` reports each result.

`profile_verdict: verified` means all required checks passed. `unverified` has a failure class: `invalid` for a demonstrated mismatch, or `unverifiable` when required evidence is missing or unsupported. Absent context is optional and does not become an invented empty object. `expired: true` can accompany a verified historical record; it does not permit a new action. Profile verification always returns `authorized: false`.

Fresh Bitcoin proofs can still be pending. Enable **Refresh timestamp proofs** when checking again later: the tool fetches current proofs, keeps your original `receipt_json`, and returns the exact checked envelope separately as `verified_receipt_json`. It never rebuilds a receipt from redacted public payload fields. Save both versions when the proofs change. One valid supported anchor is sufficient unless the receipt's retained witness policy requires more.

This is an issuer-hosted check of nested payload receipts, using Asqav's retained public keys and history. External timestamp certificates must chain to Asqav's pinned roots. Bitcoin proof verification uses Blockstream's HTTPS API for best-chain headers and checks the header hash, proof of work and Merkle commitment; it is not an independent Bitcoin node. Missing keys, history, policy material or proofs remain unavailable. Known unsupported receipt families are never reported as verified.

ID-only checks remain available for existing nodes, returning the hosted signature rollup and granular details. They do not establish an exact-receipt profile pass. Revision 09 is an unpublished individual draft, not an IETF standard or certification.

## Request Action

Provide an `action_type` and optional `params`, with the same JSON-object or plain-text format as Sign Action context. The tool returns the session ID and status immediately, with approval counts and expiry.

Request Action has no `authorized` output and does not wait for approvals. To protect a later step, keep the workflow stopped while the session is pending. Collect approvals through Asqav and query the session through the Asqav API. Continue only after checking that the matching session is approved and unexpired. Treat an expired or rejected session as a stop. Stop if the session is missing or the check fails. Session approval and execution of your workflow step are separate operations.

The plugin exposes session creation. Approval collection and status polling require separate API calls or workflow logic. See [Asqav documentation](https://asqav.com/docs) for the signing-group API.

## Agent apps

Adding these tools makes them available to the agent. Coverage depends on whether the agent calls them; it does not automatically capture every action. Use explicit workflow nodes and branches when a step must require authorization.

## Data handling

Sign Action sends the complete supplied context to `api.asqav.com`, and Request Action sends the complete supplied parameters. Profile mode derives the action reference and checks the context digest locally, but still sends the full context to Asqav. Omit sensitive data you do not want sent to Asqav. Verify Signature sends the full receipt and optional original context when exact-receipt inputs are supplied. Running the Python SDK separately does not change this plugin's request path.

Asqav's service processes those requests under its [privacy policy](https://asqav.com/privacy). The plugin does not write payloads to its own local storage; Dify manages credentials and workflow data under your deployment's settings. Execution logs may retain those inputs or outputs. See the [plugin privacy declaration](https://github.com/jagmarques/dify-plugin-asqav/blob/main/PRIVACY.md) for the transmitted fields.

## Changes in 0.0.8

Adds profile observation capture, canonical action references, run correlation, retained receipt exports and exact-receipt verification through the shared Asqav verifier. Existing nodes retain Standard mode. Profile observations never authorize execution. Updated setup and tool descriptions distinguish signing, verification and optional Enterprise approvals.

## Changes in 0.0.7

This update validates API response fields before emitting workflow outputs and corrects nullable output declarations for Dify's variable selectors. It also updates account, key and agent setup instructions. After upgrading from 0.0.6, check the existing nodes' selected outputs and retest the true, false and error routes. Source changes do not update an already installed package.

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

The plugin is source-available under the [Elastic License 2.0](https://github.com/jagmarques/dify-plugin-asqav/blob/main/LICENSE). The complete license terms are included in the package.

[Asqav website](https://www.asqav.com/) · [Documentation](https://www.asqav.com/docs) · [Plugin source](https://github.com/jagmarques/dify-plugin-asqav) · [Python SDK](https://pypi.org/project/asqav/)

Protocol background: [Compliance Profile of Signed Action Receipts for AI Agents](https://datatracker.ietf.org/doc/draft-marques-asqav-compliance-receipts/), an individual Internet-Draft (work in progress).

Contact: info@asqav.com
