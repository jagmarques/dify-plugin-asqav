# Asqav Dify Plugin

Asqav adds AI agent governance to your Dify workflows. It checks every agent action against your policies before it runs, blocks anything out of bounds, and cryptographically signs the rest into a tamper-evident audit trail you can verify later.

## Overview

Asqav is the evidence layer for AI agents. This plugin connects your Dify deployment to the Asqav API so that each action an agent takes is reviewed before your workflow commits to it. When an action is allowed, it is signed with ML-DSA-65 (a post-quantum signature) and recorded in a verifiable audit trail. When an action is blocked, you get a forensic record of the attempt instead. Either way, you end up with provable evidence of what your agents tried to do, which makes compliance reviews and incident investigations far easier.

The plugin calls the Asqav cloud API directly from your Dify deployment. Only a minimal metadata bag (action type, agent ID, session ID, model name, and tool name) is retained alongside a hash of the rest, in line with GDPR data minimization. If you prefer client-side hashing, you can run the Asqav Python SDK in hash-only mode alongside this plugin.

## Configuration

Setting up Asqav takes three short steps:

- **Get your API key:** sign up at asqav.com and create an API key. It starts with `sk_`.
- **Create an agent:** create an agent through the Asqav dashboard or SDK. Its ID starts with `agent_`.
- **Authorize the plugin:** in Dify, go to Plugins, open Asqav, and enter your API key and Agent ID to enable the tool.

## Tools

The Asqav plugin provides three actions for governing and proving agent activity.

### Sign Action

Signs an agent action with ML-DSA-65. You provide an action type, such as `read:data` or `tool:execute`, plus optional context. The response includes an `authorized` flag so your workflow can branch on the decision instead of failing. An allowed action returns its signature, identifiers, timestamp, and a public verification URL. A blocked action returns a clear reason along with a signed denial receipt that is itself verifiable.

### Verify Signature

Verifies a signature by its ID. This is a public action that needs no authentication, so anyone can confirm that a given action was genuinely signed, who signed it, when, and with which algorithm.

### Request Action

Creates a multi-party signing session for high-risk actions. The action stays pending until enough approvers have signed off, which makes it a natural pre-execution gate for sensitive steps in a workflow.

## Usage

Asqav fits into both Chatflow / Workflow apps and Agent apps:

- **Chatflow or Workflow:** add an Asqav node before the step you want to govern, choose the Sign Action or Request Action tool, and branch on the `authorized` result so the workflow only proceeds when the action is permitted.
- **Agent app:** add the Asqav tool so the agent signs its actions as it works, building a verifiable record of everything it does without changing how the agent behaves.

## Resources

- **Documentation:** [asqav.com/docs](https://asqav.com/docs)
- **Python SDK:** [PyPI](https://pypi.org/project/asqav/)
- **Plugin source:** [GitHub](https://github.com/jagmarques/dify-plugin-asqav)

## Contact

Built by Asqav. Learn more at [asqav.com](https://asqav.com).
