# Privacy Policy

## Data sent to Asqav

The plugin calls `https://api.asqav.com/api/v1`. It sends:

- The API key in an authentication header for credential validation, signing, and approval-session creation.
- The configured Agent ID for agent lookup, signing, and approval-session creation.
- The action type, full user-provided context, and optional action reference for Sign Action.
- The action type and full user-provided parameters for Request Action.
- The Signature ID for a public verification lookup, without an API-key header.

Context and parameters may contain personal or sensitive information if you include it. Plain text is wrapped in a `raw` field and sent intact. The plugin does not remove personal data or hash payloads before transmission. Send only the information your workflow needs and that you are permitted to share.

## Processing and storage

Asqav uses these requests to validate access, evaluate and sign submitted actions, create approval sessions, or return verification results. Cryptographic operations happen in the Asqav service. Service retention and data handling are covered by the [Asqav privacy policy](https://asqav.com/privacy).

The plugin does not write payloads to local files or use Dify's plugin storage API. Dify manages the configured credentials and may retain workflow inputs, outputs, and execution logs according to your deployment's settings. Network services also receive the connection information needed to serve requests.

## Contact

For privacy inquiries, contact info@asqav.com.

[Plugin source](https://github.com/jagmarques/dify-plugin-asqav)
