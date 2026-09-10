# Privacy Policy

## Data sent to Asqav

The plugin calls `https://api.asqav.com/api/v1`. It sends:

- The API key is sent in an authentication header for credential validation and signing. Approval-session creation uses the same header.
- The configured Agent ID identifies the agent for lookup and signing. Approval-session creation uses the same ID.
- Sign Action sends the action type and complete user-provided context. It also sends an optional action reference.
- The action type and full user-provided parameters for Request Action.
- The Signature ID for a public verification lookup, without an API-key header.

Context and parameters may contain personal or sensitive information if you include it. Plain text is wrapped in a `raw` field and sent intact. Profile mode computes canonical hashes locally, but sends the original context in full; hashing does not hide or replace that data. The plugin does not remove personal data. Send only the information your workflow needs and that you are permitted to share.

Exact-receipt verification sends the supplied receipt and optional original context to `api.asqav.com`. Refreshing timestamp proofs reads public anchor evidence and returns the original and checked envelopes separately; it does not replace the original payload with public redacted fields. These verification requests send no API key. Dify may retain the inputs and outputs in workflow logs.

## Processing and storage

Asqav uses these requests to validate access, evaluate and sign submitted actions, create approval sessions, or return verification results. Signing and cryptographic proof verification happen in the Asqav service. The plugin computes canonical hashes locally to bind requests and responses. Service retention and data handling are covered by the [Asqav privacy policy](https://asqav.com/privacy).

The plugin does not write payloads to local files or use Dify's plugin storage API. Dify manages the configured credentials. Your deployment settings control retention of workflow inputs and outputs, including any execution logs. Network services receive the connection information needed to serve requests.

Profile observation mode also sends `compliance_mode`, `capture_topology`, the derived `action_ref`, the workflow `iteration_id`, and the observation request fields. The returned receipt contains signed identifiers and metadata; Dify may retain it in workflow logs. The original context is still sent in full.

## Contact

For privacy inquiries, contact info@asqav.com.

[Plugin source](https://github.com/jagmarques/dify-plugin-asqav)
