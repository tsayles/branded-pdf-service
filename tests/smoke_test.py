# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
smoke_test.py
─────────────────────────────────────────────────────────────────────────────
Integration smoke test: POST to /render with the acme-corp brand and assert
we get back a non-empty application/pdf response.

Requires the service to be running. Set PDF_SERVICE_URL to override the
default http://localhost:8100.

Run:
    pytest tests/smoke_test.py -v
    PDF_SERVICE_URL=http://docker-host-2:8100 pytest tests/smoke_test.py -v
"""

import os
import pytest
import requests

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("PDF_SERVICE_URL", "http://localhost:8100")

SAMPLE_MARKDOWN = """
# Acme Corporation Test Document

This is a smoke-test document rendered by the automated test suite.

## Section One

A paragraph of body text to verify font rendering and layout.

- Item one
- Item two
- Item three

## Section Two

| Column A | Column B | Column C |
|----------|----------|----------|
| Alpha    | Beta     | Gamma    |
| Delta    | Epsilon  | Zeta     |

> This is a blockquote to verify the callout style renders correctly.

---

*End of smoke-test document.*
"""


@pytest.fixture(scope="module")
def api_key():
    """Return the API key from env, or None if auth is not yet enabled."""
    return os.environ.get("PDF_API_KEY")


def auth_headers(api_key):
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def test_healthz():
    """GET /healthz should return 200 with status ok."""
    resp = requests.get(f"{BASE_URL}/healthz", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_list_brands():
    """GET /brands should return a list containing acme-corp."""
    resp = requests.get(f"{BASE_URL}/brands", timeout=10)
    assert resp.status_code == 200
    brands = resp.json()
    assert isinstance(brands, list)
    assert "acme-corp" in brands


def test_render_acme_corp(api_key):
    """POST /render with acme-corp brand returns a valid PDF."""
    resp = requests.post(
        f"{BASE_URL}/render",
        json={"brand": "acme-corp", "markdown": SAMPLE_MARKDOWN},
        headers=auth_headers(api_key),
        timeout=60,
    )
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    # PDF magic bytes
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000


def test_render_with_meta(api_key):
    """POST /render with metadata produces a PDF with the meta block."""
    resp = requests.post(
        f"{BASE_URL}/render",
        json={
            "brand": "acme-corp",
            "markdown": "# Test\n\nBody paragraph.",
            "meta": {
                "prepared_by": "Automated Test Suite",
                "date": "2026-01-01",
                "subject": "Meta Block Test",
                "status": "DRAFT",
            },
        },
        headers=auth_headers(api_key),
        timeout=60,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_render_with_watermark(api_key):
    """POST /render with watermark='DRAFT' returns a PDF."""
    resp = requests.post(
        f"{BASE_URL}/render",
        json={
            "brand": "acme-corp",
            "markdown": "# Watermark Test\n\nThis document has a watermark.",
            "watermark": "DRAFT",
        },
        headers=auth_headers(api_key),
        timeout=60,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_render_unknown_brand(api_key):
    """POST /render with an unknown brand returns 400."""
    resp = requests.post(
        f"{BASE_URL}/render",
        json={"brand": "no-such-brand", "markdown": "# Test"},
        headers=auth_headers(api_key),
        timeout=30,
    )
    assert resp.status_code == 400
