## Privacy Policy

### Data Collection

This plugin sends the following data to the asqav API (api.asqav.com):

- **Action type**: A string label describing the agent action being signed (e.g., "read:data").
- **Context payload**: A JSON object with metadata about the action. This is user-provided and may contain any data the user chooses to include.
- **Agent ID**: The identifier of the asqav agent performing the signing.
- **Signature ID**: Used for verification lookups (public endpoint, no authentication required).

### Data Not Collected

- No personal user data is collected by this plugin.
- No IP addresses, email addresses, or user identifiers are transmitted.
- The plugin does not store any data locally.

### Third-Party Service

All cryptographic operations are performed server-side by the asqav API. The asqav API key is transmitted as an HTTP header for authentication. See https://asqav.com/privacy for the full asqav privacy policy.

### Contact

For privacy inquiries, contact: privacy@asqav.com
Repository: https://github.com/jagmarques/dify-plugin-asqav
