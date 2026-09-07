# Privacy Policy

## Data sent to Asqav

The plugin calls `https://api.asqav.com/api/v1`. It sends:

- The API key authenticates credential validation and signing requests. It also authenticates approval-session creation.
- The configured Agent ID identifies the agent for lookup and signing. Approval-session creation uses the same ID.
- Sign Action sends the action type and complete user-provided context. It also sends an optional action reference.
- The action type and full user-provided parameters for Request Action.
- The Signature ID for a public verification lookup, without an API-key header.

Context and parameters may contain personal or sensitive information if you include it. Plain text is wrapped in a `raw` field and sent intact. The plugin does not remove personal data or hash payloads before transmission. Send only the information your workflow needs and that you are permitted to share.

## Processing and storage

Asqav uses these requests to validate access, evaluate and sign submitted actions, create approval sessions, or return verification results. Cryptographic operations happen in the Asqav service. Service retention and data handling are covered by the [Asqav privacy policy](https://asqav.com/privacy).

The plugin does not write payloads to local files or use Dify's plugin storage API. Dify manages the configured credentials. Your deployment settings control retention of workflow inputs and outputs, including any execution logs. Network services receive the connection information needed to serve requests.

## Contact

For privacy inquiries, contact info@asqav.com.

[Plugin source](https://github.com/jagmarques/dify-plugin-asqav)
