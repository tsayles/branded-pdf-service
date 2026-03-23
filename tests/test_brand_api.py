# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
test_brand_api.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the brand management API endpoints.

Uses FastAPI's TestClient (via httpx) with a temporary BRANDS_DIR, so
no running container is required.  The validate_brand_typ() and
render_document() functions are mocked to avoid needing Typst/Pandoc
binaries in the unit test environment.
"""

import io
import json
import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_brands_dir(tmp_path, monkeypatch):
    """Redirect BRANDS_DIR to a temporary directory for each test.

    Creates an 'acme-test' brand in the temp dir so list endpoints
    always have at least one brand.
    """
    brands_root = tmp_path / "brands"
    brands_root.mkdir()

    acme_dir = brands_root / "acme-test"
    acme_dir.mkdir()
    meta = {
        "org_name": "Acme Test Corp",
        "footer_text": "Acme Test Corp • Test",
        "default_font": "Liberation Sans",
        "heading_font": "Liberation Serif",
    }
    (acme_dir / "meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    (acme_dir / "brand.typ").write_text(
        "#set page(paper: \"us-letter\")\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("BRANDS_DIR", str(brands_root))

    import app.renderer as renderer
    import app.main as main_module

    renderer.BRANDS_DIR = str(brands_root)
    main_module.BRANDS_DIR = str(brands_root)

    yield str(brands_root)


@pytest.fixture
def client():
    """Return a TestClient for the FastAPI app."""
    from app.main import app
    return TestClient(app)


# ── GET /brands/{slug} ────────────────────────────────────────────────────────


class TestGetBrandMeta:
    """Tests for GET /brands/{slug}."""

    def test_returns_meta_for_known_brand(self, client):
        """GET /brands/acme-test returns slug and meta."""
        resp = client.get("/brands/acme-test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "acme-test"
        assert data["meta"]["org_name"] == "Acme Test Corp"

    def test_404_for_unknown_brand(self, client):
        """GET /brands/no-such-brand returns 404."""
        resp = client.get("/brands/no-such-brand")
        assert resp.status_code == 404

    def test_400_for_invalid_slug(self, client):
        """GET /brands/INVALID returns 400."""
        resp = client.get("/brands/INVALID_SLUG")
        assert resp.status_code == 400


# ── POST /brands/{slug} ───────────────────────────────────────────────────────


class TestUploadBrand:
    """Tests for POST /brands/{slug}."""

    _VALID_META = json.dumps({
        "org_name": "Test Corp",
        "footer_text": "Test Corp • Footer",
        "default_font": "Liberation Sans",
        "heading_font": "Liberation Serif",
    })
    _VALID_TYP = "#set page(paper: \"us-letter\")\n"
    _FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    def _post(self, client, slug, meta=None, typ=None, logo=None):
        data = {
            "meta_json": meta or self._VALID_META,
            "brand_typ": typ or self._VALID_TYP,
        }
        files = {}
        if logo is not False:
            if logo is None:
                pass  # no logo
            else:
                files["logo"] = (
                    "logo.png", io.BytesIO(logo), "image/png"
                )
        with patch("app.main.validate_brand_typ"):
            return client.post(
                f"/brands/{slug}",
                data=data,
                files=files or None,
            )

    def test_creates_new_brand(self, client, isolated_brands_dir):
        """POST /brands/new-corp creates brand, returns 201."""
        resp = self._post(client, "new-corp")
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "new-corp"
        assert data["created"] is True
        assert os.path.isdir(
            os.path.join(isolated_brands_dir, "new-corp")
        )

    def test_updates_existing_brand(self, client, isolated_brands_dir):
        """POST /brands/acme-test updates brand, returns 200."""
        resp = self._post(client, "acme-test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is False

    def test_saves_logo_when_provided(self, client, isolated_brands_dir):
        """POST with logo saves logo.png to brand directory."""
        resp = self._post(client, "logo-test", logo=self._FAKE_PNG)
        assert resp.status_code == 201
        logo_path = os.path.join(
            isolated_brands_dir, "logo-test", "logo.png"
        )
        assert os.path.exists(logo_path)

    def test_rejects_invalid_json(self, client):
        """POST with malformed meta_json returns 400."""
        data = {
            "meta_json": "{not valid json",
            "brand_typ": self._VALID_TYP,
        }
        with patch("app.main.validate_brand_typ"):
            resp = client.post("/brands/bad-meta", data=data)
        assert resp.status_code == 400

    def test_rejects_non_png_logo(self, client):
        """POST with a non-PNG logo returns 400."""
        data = {
            "meta_json": self._VALID_META,
            "brand_typ": self._VALID_TYP,
        }
        files = {"logo": ("logo.jpg", io.BytesIO(b"JFIF..."), "image/jpeg")}
        with patch("app.main.validate_brand_typ"):
            resp = client.post("/brands/bad-logo", data=data, files=files)
        assert resp.status_code == 400

    def test_rejects_invalid_brand_typ(self, client):
        """POST with a brand.typ that fails to compile returns 400."""
        data = {
            "meta_json": self._VALID_META,
            "brand_typ": "#invalid-typst-syntax {{ broken",
        }
        with patch(
            "app.main.validate_brand_typ",
            side_effect=ValueError("brand.typ failed to compile: error"),
        ):
            resp = client.post("/brands/broken-brand", data=data)
        assert resp.status_code == 400
        assert "failed to compile" in resp.json()["detail"]

    def test_400_for_invalid_slug(self, client):
        """POST with an invalid slug returns 400."""
        data = {
            "meta_json": self._VALID_META,
            "brand_typ": self._VALID_TYP,
        }
        with patch("app.main.validate_brand_typ"):
            resp = client.post("/brands/INVALID__SLUG", data=data)
        assert resp.status_code == 400


# ── DELETE /brands/{slug} ─────────────────────────────────────────────────────


class TestDeleteBrand:
    """Tests for DELETE /brands/{slug}."""

    def _create_extra_brand(self, brands_dir, name="extra-brand"):
        """Create a minimal brand directory in brands_dir."""
        bdir = os.path.join(brands_dir, name)
        os.makedirs(bdir, exist_ok=True)
        with open(
            os.path.join(bdir, "meta.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump({"org_name": "Extra"}, fh)
        with open(
            os.path.join(bdir, "brand.typ"), "w", encoding="utf-8"
        ) as fh:
            fh.write("#set page()\n")

    def test_deletes_brand(self, client, isolated_brands_dir):
        """DELETE removes a brand when a second brand exists."""
        self._create_extra_brand(isolated_brands_dir)
        resp = client.delete("/brands/acme-test")
        assert resp.status_code == 204
        assert not os.path.isdir(
            os.path.join(isolated_brands_dir, "acme-test")
        )

    def test_404_for_unknown_brand(self, client):
        """DELETE /brands/no-such returns 404."""
        resp = client.delete("/brands/no-such")
        assert resp.status_code == 404

    def test_409_prevents_last_brand_deletion(self, client):
        """DELETE returns 409 when only one brand remains."""
        resp = client.delete("/brands/acme-test")
        assert resp.status_code == 409
        assert "last" in resp.json()["detail"].lower()

    def test_400_for_invalid_slug(self, client):
        """DELETE with an invalid slug returns 400."""
        resp = client.delete("/brands/INVALID")
        assert resp.status_code == 400


# ── GET /brands/{slug}/preview ────────────────────────────────────────────────


class TestPreviewBrand:
    """Tests for GET /brands/{slug}/preview."""

    def test_returns_pdf_for_known_brand(self, client):
        """Preview returns a valid PDF response."""
        fake_pdf = b"%PDF-1.4 fake content"
        with patch(
            "app.main.render_document", return_value=fake_pdf
        ):
            resp = client.get("/brands/acme-test/preview")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/pdf"
        assert resp.content == fake_pdf

    def test_404_for_unknown_brand(self, client):
        """Preview returns 404 for an unknown brand."""
        with patch(
            "app.main.render_document",
            side_effect=ValueError("Brand 'no-such' not found"),
        ):
            resp = client.get("/brands/no-such/preview")
        assert resp.status_code == 404

    def test_400_for_invalid_slug(self, client):
        """Preview returns 400 for an invalid slug."""
        resp = client.get("/brands/BAD__SLUG/preview")
        assert resp.status_code == 400
