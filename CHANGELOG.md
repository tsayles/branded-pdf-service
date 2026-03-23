# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.2.1] -- 2026-03-23

### Fixed
- CI: `docker/build-push-action@v5` with `push: false` does not load the
  built image into the local Docker daemon without `load: true`; the
  `Smoke-test healthz` step was failing with "pull access denied" (#8)
- CI: `pytest tests/ -v` collected `smoke_test.py` which makes live HTTP
  requests — added `pytestmark = pytest.mark.integration` and run unit
  tests with `-m "not integration"` to exclude live-service tests (#8)

### Added
- `pytest.ini` registering the `integration` marker
- CI: expanded test dependencies (`python-multipart`, `httpx`, `mcp`)
- CI: replaced fixed `sleep 15` healthz wait with a 60-second polling loop

---

## [0.2.0] -- 2026-03-23

### Added
- `GET /brands/{slug}` -- brand metadata endpoint (open, no auth required)
- `POST /brands/{slug}` -- upload/replace a brand at runtime (multipart;
  Typst template validated before save) (#2)
- `DELETE /brands/{slug}` -- remove a brand; last-brand guard returns 409 (#2)
- `GET /brands/{slug}/preview` -- render a one-page brand preview PDF (#2)
- `app/auth.py` -- Bearer token authentication via `PDF_API_KEYS` env var
  (comma-separated) or `PDF_API_KEYS_FILE`; open mode when unset (#4)
- `app/keygen.py` -- `python -m app.keygen` generates a 32-byte URL-safe
  token (#4)
- `app/mcp_server.py` -- FastMCP stdio server exposing 5 tools:
  `render_pdf`, `list_brands`, `get_brand_meta`, `upload_brand`,
  `preview_brand` (#6)
- `tests/test_brand_api.py` -- 17 unit tests for brand management endpoints
- `tests/test_auth.py` -- 20 unit tests for auth (open and keyed mode)
- `tests/test_mcp_server.py` -- 13 unit tests for MCP tools

### Changed
- `app/main.py`: FastAPI lifespan context manager replaces deprecated
  `on_event`; version bumped to 0.2.0
- Protected endpoints (`POST /render`, `POST/DELETE /brands/{slug}`,
  `GET /brands/{slug}/preview`) require `Authorization: Bearer <token>`
  when auth is enabled
- `requirements.txt`: added `python-multipart>=0.0.9`, `mcp[cli]>=1.0.0`

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

[Unreleased]: https://github.com/tsayles/branded-pdf-service/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/tsayles/branded-pdf-service/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/tsayles/branded-pdf-service/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tsayles/branded-pdf-service/releases/tag/v0.1.0
