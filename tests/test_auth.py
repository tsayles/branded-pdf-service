# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
test_auth.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the Bearer token authentication module.

Tests cover:
- open mode (no keys configured)
- protected mode (keys configured)
- open endpoints remain unauthenticated
- protected endpoints require valid Bearer token
- keygen produces distinct, URL-safe tokens
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ── Auth module unit tests ────────────────────────────────────────────────────


class TestKeyLoading:
    """Tests for app.auth._load_keys()."""

    def test_empty_when_no_keys_configured(self, monkeypatch):
        """Returns empty set when no env var and no key file."""
        monkeypatch.delenv("PDF_API_KEYS", raising=False)
        monkeypatch.setenv("PDF_API_KEYS_FILE", "/nonexistent/path.txt")
        from app.auth import _load_keys
        assert _load_keys() == frozenset()

    def test_loads_from_env_var(self, monkeypatch):
        """Parses comma-separated keys from PDF_API_KEYS."""
        monkeypatch.setenv("PDF_API_KEYS", "key1, key2, key3 ")
        monkeypatch.setenv("PDF_API_KEYS_FILE", "/nonexistent/path.txt")
        from app.auth import _load_keys
        keys = _load_keys()
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_loads_from_key_file(self, monkeypatch, tmp_path):
        """Reads keys from file, one per line, ignores comments."""
        key_file = tmp_path / "api-keys.txt"
        key_file.write_text("# comment\nfilekey1\nfilekey2\n", encoding="utf-8")
        monkeypatch.delenv("PDF_API_KEYS", raising=False)
        monkeypatch.setenv("PDF_API_KEYS_FILE", str(key_file))
        from app.auth import _load_keys
        keys = _load_keys()
        assert "filekey1" in keys
        assert "filekey2" in keys
        assert "# comment" not in keys

    def test_merges_env_and_file(self, monkeypatch, tmp_path):
        """Keys from env var and file are combined."""
        key_file = tmp_path / "api-keys.txt"
        key_file.write_text("filekey\n", encoding="utf-8")
        monkeypatch.setenv("PDF_API_KEYS", "envkey")
        monkeypatch.setenv("PDF_API_KEYS_FILE", str(key_file))
        from app.auth import _load_keys
        keys = _load_keys()
        assert "envkey" in keys
        assert "filekey" in keys


# ── Endpoint-level auth tests ─────────────────────────────────────────────────


@pytest.fixture
def isolated_brands_dir(tmp_path, monkeypatch):
    """Set up a temp brands dir with acme-test brand."""
    import json
    brands_root = tmp_path / "brands"
    brands_root.mkdir()
    acme_dir = brands_root / "acme-test"
    acme_dir.mkdir()
    meta = {"org_name": "Test", "footer_text": "Test", "default_font": "Liberation Sans", "heading_font": "Liberation Serif"}
    (acme_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (acme_dir / "brand.typ").write_text("#set page()\n", encoding="utf-8")

    monkeypatch.setenv("BRANDS_DIR", str(brands_root))
    import app.renderer as renderer
    import app.main as main_module
    renderer.BRANDS_DIR = str(brands_root)
    main_module.BRANDS_DIR = str(brands_root)
    yield str(brands_root)


@pytest.fixture
def open_client(isolated_brands_dir, monkeypatch):
    """TestClient with auth DISABLED (no keys configured)."""
    monkeypatch.delenv("PDF_API_KEYS", raising=False)
    monkeypatch.setenv("PDF_API_KEYS_FILE", "/nonexistent/path.txt")
    from app.main import app
    return TestClient(app)


@pytest.fixture
def authed_client(isolated_brands_dir, monkeypatch):
    """TestClient with auth ENABLED (test-key configured)."""
    monkeypatch.setenv("PDF_API_KEYS", "test-secret-key-abc123")
    monkeypatch.setenv("PDF_API_KEYS_FILE", "/nonexistent/path.txt")
    from app.main import app
    return TestClient(app)


class TestOpenMode:
    """Auth is disabled — all endpoints accessible without token."""

    def test_healthz_open(self, open_client):
        """GET /healthz succeeds in open mode."""
        resp = open_client.get("/healthz")
        assert resp.status_code == 200

    def test_brands_list_open(self, open_client):
        """GET /brands succeeds in open mode."""
        resp = open_client.get("/brands")
        assert resp.status_code == 200

    def test_render_open(self, open_client):
        """POST /render succeeds without auth in open mode."""
        with patch("app.main.render_document", return_value=b"%PDF-fake"):
            resp = open_client.post(
                "/render",
                json={"brand": "acme-test", "markdown": "# Test"},
            )
        assert resp.status_code == 200

    def test_brand_delete_open(self, open_client, isolated_brands_dir):
        """DELETE /brands/{slug} allowed in open mode if 2nd brand exists."""
        import json
        extra = os.path.join(isolated_brands_dir, "extra")
        os.makedirs(extra)
        with open(os.path.join(extra, "meta.json"), "w") as f:
            json.dump({"org_name": "E"}, f)
        with open(os.path.join(extra, "brand.typ"), "w") as f:
            f.write("#set page()\n")
        resp = open_client.delete("/brands/extra")
        assert resp.status_code == 204


class TestProtectedMode:
    """Auth is enabled — protected endpoints require Bearer token."""

    def test_healthz_still_open(self, authed_client):
        """GET /healthz remains unauthenticated even when auth is on."""
        resp = authed_client.get("/healthz")
        assert resp.status_code == 200

    def test_brands_list_still_open(self, authed_client):
        """GET /brands remains unauthenticated when auth is on."""
        resp = authed_client.get("/brands")
        assert resp.status_code == 200

    def test_get_brand_meta_still_open(self, authed_client):
        """GET /brands/{slug} (read) remains unauthenticated."""
        resp = authed_client.get("/brands/acme-test")
        assert resp.status_code == 200

    def test_render_requires_token(self, authed_client):
        """POST /render returns 401 without token."""
        with patch("app.main.render_document", return_value=b"%PDF-fake"):
            resp = authed_client.post(
                "/render",
                json={"brand": "acme-test", "markdown": "# Test"},
            )
        assert resp.status_code == 401

    def test_render_accepts_valid_token(self, authed_client):
        """POST /render succeeds with valid Bearer token."""
        with patch("app.main.render_document", return_value=b"%PDF-fake"):
            resp = authed_client.post(
                "/render",
                json={"brand": "acme-test", "markdown": "# Test"},
                headers={"Authorization": "Bearer test-secret-key-abc123"},
            )
        assert resp.status_code == 200

    def test_render_rejects_wrong_token(self, authed_client):
        """POST /render returns 401 with an invalid token."""
        with patch("app.main.render_document", return_value=b"%PDF-fake"):
            resp = authed_client.post(
                "/render",
                json={"brand": "acme-test", "markdown": "# Test"},
                headers={"Authorization": "Bearer wrong-key"},
            )
        assert resp.status_code == 401

    def test_preview_requires_token(self, authed_client):
        """GET /brands/{slug}/preview returns 401 without token."""
        with patch("app.main.render_document", return_value=b"%PDF-fake"):
            resp = authed_client.get("/brands/acme-test/preview")
        assert resp.status_code == 401

    def test_upload_requires_token(self, authed_client):
        """POST /brands/{slug} returns 401 without token."""
        import json as json_module
        data = {
            "meta_json": json_module.dumps({"org_name": "X"}),
            "brand_typ": "#set page()\n",
        }
        with patch("app.main.validate_brand_typ"):
            resp = authed_client.post("/brands/new-brand", data=data)
        assert resp.status_code == 401

    def test_delete_requires_token(self, authed_client):
        """DELETE /brands/{slug} returns 401 without token."""
        resp = authed_client.delete("/brands/acme-test")
        assert resp.status_code == 401


# ── Keygen tests ──────────────────────────────────────────────────────────────


class TestKeygen:
    """Tests for app.keygen."""

    def test_generates_non_empty_key(self):
        """generate_key() returns a non-empty string."""
        from app.keygen import generate_key
        key = generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generates_url_safe_key(self):
        """generate_key() returns only URL-safe characters."""
        from app.keygen import generate_key
        import re
        for _ in range(10):
            key = generate_key()
            assert re.match(r'^[A-Za-z0-9_\-]+$', key), (
                f"Key contains non-URL-safe chars: {key}"
            )

    def test_generates_distinct_keys(self):
        """generate_key() produces unique keys."""
        from app.keygen import generate_key
        keys = {generate_key() for _ in range(20)}
        assert len(keys) == 20
