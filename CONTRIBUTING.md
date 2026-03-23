# Contributing to branded-pdf-service

Thank you for your interest in contributing!

## Development setup

```bash
git clone https://github.com/tsayles/branded-pdf-service
cd branded-pdf-service
pip install -r requirements.txt
pip install pytest requests
```

## Running tests

Unit tests (no Docker required):
```bash
pytest tests/test_brand_loader.py -v
```

Integration smoke tests (requires running container):
```bash
docker compose up -d
pytest tests/smoke_test.py -v
docker compose down
```

## Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/short-description` | `feat/brand-management-api` |
| Bug fix | `fix/short-description` | `fix/watermark-rotation` |
| Docs | `docs/short-description` | `docs/mcp-quickstart` |
| Chore | `chore/short-description` | `chore/bump-typst-0-15` |

## Submitting a PR

1. Fork the repo and create a branch from `main`.
2. Write or update tests for your change.
3. Ensure `pytest tests/test_brand_loader.py` passes.
4. Add a CHANGELOG entry under `[Unreleased]`.
5. Add SPDX license header to any new source files.
6. Open a PR — the template will guide you through the checklist.

## Brand configs

Brand configs (`brands/*/`) are **not** accepted in PRs. The `brands/` directory
is gitignored and volume-mounted at runtime. Use the brand management API
(Phase 5 of the roadmap) to share brand templates with the community.

## Code style

- Python: follow PEP 8. No formatter is enforced yet; just be consistent.
- Typst templates: follow the structure of `brands/acme-corp/brand.typ`.
- Commit messages: use conventional commits (`feat:`, `fix:`, `chore:`, `docs:`).
- All new `.py` files must have an SPDX header.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
