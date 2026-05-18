# Changelog

All notable changes to `dify-plugin-asqav` are listed here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/) and track the manifest version (`manifest.yaml`).

## [Unreleased]

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
