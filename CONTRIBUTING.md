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

- **Python — PEP 8:** Follow [PEP 8](https://peps.python.org/pep-0008/) for all
  Python source files. No formatter is enforced yet; just be consistent with the
  surrounding code.
- **Line length — 80 columns:** Hard-wrap all Python source lines at **80
  characters**. This applies to code, inline comments, and docstrings. The
  existing source files use 80-col wrapping; new contributions must match.
  Configure your editor accordingly (e.g. `rulers = [80]` in VS Code,
  `set colorcolumn=80` in Vim).
- **Docstrings — PEP 257:** All public modules, classes, functions, and methods
  must have a docstring conforming to [PEP 257](https://peps.python.org/pep-0257/).
  Use the multi-line Google-style format already established in the codebase:
  summary line, blank line, then named sections (`Args:`, `Returns:`,
  `Raises:`) as needed. One-liner docstrings are acceptable only for trivial
  private helpers.
- **Typst templates:** Follow the structure of `brands/acme-corp/brand.typ`
  (section comments, colour variables first, then page/text/heading/quote/table
  rules in that order).
- **Commit messages:** Use conventional commits (`feat:`, `fix:`, `chore:`,
  `docs:`).
- **SPDX headers:** All new `.py` files must start with:
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  # SPDX-FileCopyrightText: <year> <your name>
  ```

## Merge strategy

**This project uses squash merge for all feature and fix branches.**

Rationale: each feature or fix PR represents a single logical unit of change.
Squashing collapses the granular implementation commits (which are not
meaningful to the project history) into one well-described commit on `main`,
keeping the main-branch log readable as a high-level changelog. The individual
commits are still visible in the PR for reviewers.

When merging a PR:
1. Use **"Squash and merge"** in the GitHub UI (or `gh pr merge --squash`).
2. Edit the squash commit message to be a well-formed conventional-commit
   summary, e.g. `feat(brands): add runtime brand management API (#12)`.
3. Delete the branch after merging.

Merge commits (non-squash) are reserved for release integration branches where
preserving the full branch history is important (e.g., backport merges).

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
