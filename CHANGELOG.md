# Changelog

All notable changes to `dify-plugin-asqav` are listed here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/) and track the manifest version (`manifest.yaml`).

## [Unreleased]

### Added
- pytest smoke suite covering the provider entrypoint and all three tools, with
  network calls mocked so the suite runs offline.
- GitHub Actions CI (`.github/workflows/ci.yml`) running pytest on Python 3.12
  (matching the plugin runner declared in `manifest.yaml`) for every PR and
  push to `main`.
- `requirements-dev.txt` listing the test dependencies, plus a Development
  section in the README explaining how to run the suite locally.

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
