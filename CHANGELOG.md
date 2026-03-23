# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Phase 5a: Brand Management API (runtime CRUD for brand configs)
- Phase 5b: KISS Authentication (Bearer token, agent-friendly)
- Phase 5c: MCP Server interface (stdio transport, agent tool manifest)

---

## [0.1.0] -- 2026-03-22

### Added
- Initial public release extracted from \	sayles/homelab\ (PR #39)
- \POST /render\ -- render Markdown to a branded PDF via Pandoc to Typst pipeline
- \GET /healthz\ -- liveness probe reporting Pandoc and Typst versions
- \GET /brands\ -- list available brand identifiers from the mounted \/brands\ volume
- \rands/acme-corp/\ -- reference demo brand (ACME Corporation, red/black aesthetic)
- Multi-stage, multi-arch Dockerfile (\linux/amd64\, \linux/arm64\)
- Non-root runtime user (\pdfservice\, UID 1001)
- OCI image labels
- HEALTHCHECK on \/healthz- GitHub Actions CI workflow (\ci.yml\) -- build + unit test on push/PR
- GitHub Actions release workflow (elease.yml\) -- multi-arch push on \*\ tag
- Unit tests for brand loader (\	ests/test_brand_loader.py\)
- Integration smoke tests (\	ests/smoke_test.py\) -- requires running container
- GPL-3.0 license
- SPDX license headers on all Python source files

### Changed
- Health endpoint renamed from \/health\ to \/healthz- Typst version bumped from 0.13.1 to 0.14.2
- Dockerfile converted from single-stage to multi-stage for smaller runtime image
- Personal brand configs removed; replaced with generic ACME Corp demo brand

### Notes
- Baseline build verification is deferred to VM 105 (docker-host-2, pve-cat)
  during Phase 6 homelab deployment. Docker is not available in the Windows
  development environment where this repo was assembled.

[Unreleased]: https://github.com/tsayles/branded-pdf-service/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tsayles/branded-pdf-service/releases/tag/v0.1.0
