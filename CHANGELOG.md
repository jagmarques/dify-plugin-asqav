# Changelog

All notable changes to `dify-plugin-asqav` are listed here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/) and track the manifest version (`manifest.yaml`).

## [Unreleased]

## [0.0.3] - 2026-05-30

### Added
- `sign_action` now returns a structured `authorized` decision. On a permitted
  action it returns `authorized=true` with the signature receipt, now including
  `signature_b64`. On a policy block, emergency halt, delegation limit, or
  agent quarantine it returns `authorized=false` with a machine `reason`
  (`policy_blocked`, `emergency_halt`, `delegation_denied`, `quarantine`, or
  `denied`) and a human-readable `detail`, so a workflow can branch on the
  decision instead of failing. A policy block also passes through the signed
  denial receipt (`signed_deny`), which is itself verifiable.
- pytest smoke suite covering the provider entrypoint and all three tools, with
  network calls mocked so the suite runs offline.
- GitHub Actions CI (`.github/workflows/ci.yml`) running pytest on Python 3.12
  (matching the plugin runner declared in `manifest.yaml`) for every PR and
  push to `main`.
- `requirements-dev.txt` listing the test dependencies, plus a Development
  section in the README explaining how to run the suite locally.
- `output_schema` declarations on all three tools (`sign_action`,
  `verify_signature`, `request_action`) so downstream workflow nodes can
  address each returned field by name.

### Changed
- Plugin user-facing text is now English-only (`en_US`). Removed the
  untranslated `zh_Hans` and `pt_BR` locale keys that duplicated the English
  strings across the manifest, provider, and tool definitions.
- README now documents the full output of each tool, including the structured
  `authorized` decision and `signature_b64` from `sign_action`.

### Fixed
- Each tool now emits its result as individual workflow variables in addition
  to the JSON message, so a Dify workflow node can address each field by name
  (`signature_id`, `authorized`, `verified`, and so on) at runtime. A JSON
  message alone left named selectors unresolved once wired in a workflow.
- The `sign_action` `timestamp` output is a Unix epoch number, not an ISO 8601
  string. Corrected its type and description in the tool schema.
- Capitalised the display label and credential prose to "Asqav" across the
  manifest, provider, and tool definitions.

## [0.0.2] - 2026-05-11

### Changed
- Public email consolidation on `info@asqav.com` across plugin metadata and provider docs (#6).
- Brand positioning rebased from post-quantum cryptography to AI compliance (#5).
- Comment hygiene sweep across plugin source and tool YAML files (#7).

### Documentation
- Capitalised "Asqav" in prose and alt text on the logo banner (#3, #4).
- Replaced canonicalization jargon with a pointer to the [SDK fingerprint spec](https://github.com/jagmarques/asqav-sdk/blob/main/docs/fingerprint-spec.md) (#2).
- Added SDK hash-only / full-payload mode notes so adopters can pick the right data-handling stance (#1).

## [0.0.1] - 2026-04-29

Initial release. Three Dify tools (Sign Action, Verify Signature, Request Action) backed by `https://api.asqav.com`.
