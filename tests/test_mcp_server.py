# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
test_mcp_server.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the MCP server tools.

Tests call the tool functions directly (not via MCP transport) to avoid
needing a running MCP client.  render_document, validate_brand_typ, and
load_brand are mocked where Pandoc/Typst binaries are unavailable.
"""

import base64
import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def isolated_brands(tmp_path, monkeypatch):
    """Temporary brands directory with acme-test brand."""
    brands_root = tmp_path / "brands"
    brands_root.mkdir()
    b = brands_root / "acme-test"
    b.mkdir()
    meta = {
        "org_name": "Acme Test",
        "footer_text": "Acme Test • Footer",
        "default_font": "Liberation Sans",
        "heading_font": "Liberation Serif",
    }
    (b / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (b / "brand.typ").write_text("#set page()\n", encoding="utf-8")
    monkeypatch.setenv("BRANDS_DIR", str(brands_root))
    monkeypatch.delenv("PDF_API_KEYS", raising=False)
    monkeypatch.setenv("PDF_API_KEYS_FILE", "/nonexistent")
    import app.renderer as renderer
    renderer.BRANDS_DIR = str(brands_root)
    import app.mcp_server as mcp_mod
    mcp_mod.BRANDS_DIR = str(brands_root)
    yield str(brands_root)


class TestListBrands:
    """Tests for the list_brands MCP tool."""

    def test_returns_known_brand(self, isolated_brands):
        """list_brands includes 'acme-test'."""
        from app.mcp_server import list_brands
        brands = list_brands()
        assert "acme-test" in brands

    def test_returns_sorted_list(self, isolated_brands):
        """list_brands returns a sorted list."""
        os.makedirs(os.path.join(isolated_brands, "z-brand"))
        os.makedirs(os.path.join(isolated_brands, "a-brand"))
        from app.mcp_server import list_brands
        brands = list_brands()
        assert brands == sorted(brands)


class TestGetBrandMeta:
    """Tests for the get_brand_meta MCP tool."""

    def test_returns_meta_for_known_brand(self):
        """get_brand_meta returns org_name for known brand."""
        from app.mcp_server import get_brand_meta
        meta = get_brand_meta("acme-test")
        assert meta["org_name"] == "Acme Test"

    def test_raises_for_unknown_brand(self):
        """get_brand_meta raises ValueError for unknown brand."""
        from app.mcp_server import get_brand_meta
        with pytest.raises(ValueError):
            get_brand_meta("no-such-brand")


class TestRenderPdf:
    """Tests for the render_pdf MCP tool."""

    _FAKE_PDF = b"%PDF-1.4 fake"

    def test_returns_base64_pdf(self):
        """render_pdf returns base64-encoded PDF."""
        with patch(
            "app.mcp_server.render_document",
            return_value=self._FAKE_PDF,
        ):
            result = __import__(
                "app.mcp_server", fromlist=["render_pdf"]
            ).render_pdf("acme-test", "# Test")
        decoded = base64.b64decode(result)
        assert decoded == self._FAKE_PDF

    def test_passes_doc_meta(self):
        """render_pdf passes title/status/etc to render_document."""
        captured = {}
        def fake_render(brand_id, sections, doc_meta, watermark):
            captured.update(doc_meta)
            return self._FAKE_PDF

        from app.mcp_server import render_pdf
        with patch("app.mcp_server.render_document", side_effect=fake_render):
            render_pdf(
                "acme-test", "# Test",
                title="My Title", status="DRAFT", prepared_by="Bot",
            )
        assert captured.get("subject") == "My Title"
        assert captured.get("status") == "DRAFT"
        assert captured.get("prepared_by") == "Bot"

    def test_auth_check_raises_when_key_missing(self, monkeypatch):
        """render_pdf raises RuntimeError when auth enabled but no key."""
        monkeypatch.setenv("PDF_API_KEYS", "valid-key")
        monkeypatch.delenv("PDF_API_KEY", raising=False)
        from app.mcp_server import render_pdf
        import importlib, app.mcp_server
        importlib.reload(app.mcp_server)
        from app.mcp_server import render_pdf as rp
        with patch("app.mcp_server.render_document", return_value=self._FAKE_PDF):
            with pytest.raises(RuntimeError, match="PDF_API_KEY"):
                rp("acme-test", "# Test")


class TestPreviewBrand:
    """Tests for the preview_brand MCP tool."""

    def test_returns_base64_pdf(self):
        """preview_brand returns base64-encoded PDF."""
        fake_pdf = b"%PDF-preview"
        with patch("app.mcp_server.render_document", return_value=fake_pdf):
            from app.mcp_server import preview_brand
            result = preview_brand("acme-test")
        assert base64.b64decode(result) == fake_pdf


class TestUploadBrand:
    """Tests for the upload_brand MCP tool."""

    _VALID_META = json.dumps({
        "org_name": "New Corp",
        "footer_text": "New Corp • Test",
        "default_font": "Liberation Sans",
        "heading_font": "Liberation Serif",
    })
    _VALID_TYP = "#set page(paper: \"us-letter\")\n"

    def test_creates_new_brand(self, isolated_brands):
        """upload_brand creates a new brand directory."""
        with patch("app.mcp_server.validate_brand_typ"):
            from app.mcp_server import upload_brand
            result = upload_brand("new-corp", self._VALID_META, self._VALID_TYP)
        assert result["slug"] == "new-corp"
        assert result["created"] is True
        assert os.path.isdir(os.path.join(isolated_brands, "new-corp"))

    def test_updates_existing_brand(self, isolated_brands):
        """upload_brand returns created=False for existing brand."""
        with patch("app.mcp_server.validate_brand_typ"):
            from app.mcp_server import upload_brand
            result = upload_brand("acme-test", self._VALID_META, self._VALID_TYP)
        assert result["created"] is False

    def test_rejects_invalid_slug(self):
        """upload_brand raises ValueError for invalid slug."""
        with patch("app.mcp_server.validate_brand_typ"):
            from app.mcp_server import upload_brand
            with pytest.raises(ValueError, match="slug"):
                upload_brand("INVALID", self._VALID_META, self._VALID_TYP)

    def test_rejects_bad_meta_json(self):
        """upload_brand raises ValueError for malformed meta_json."""
        with patch("app.mcp_server.validate_brand_typ"):
            from app.mcp_server import upload_brand
            with pytest.raises(ValueError, match="JSON"):
                upload_brand("new-brand", "{broken", self._VALID_TYP)

    def test_rejects_non_png_logo(self):
        """upload_brand raises ValueError for non-PNG logo."""
        fake_jpg = base64.b64encode(b"JFIF-not-png").decode()
        with patch("app.mcp_server.validate_brand_typ"):
            from app.mcp_server import upload_brand
            with pytest.raises(ValueError, match="PNG"):
                upload_brand(
                    "new-brand", self._VALID_META,
                    self._VALID_TYP, logo_png_base64=fake_jpg,
                )
