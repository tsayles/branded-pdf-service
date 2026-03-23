# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
test_brand_loader.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the brand loading logic in app.renderer.

These tests do not require Docker or any running service — they exercise
the load_brand() function directly against a temporary brands directory.
"""

import json
import os
import tempfile

import pytest

# Patch BRANDS_DIR before importing renderer
import importlib


@pytest.fixture
def brands_dir(tmp_path):
    """Create a temporary brands directory with a valid acme-test brand."""
    brand_dir = tmp_path / "acme-test"
    brand_dir.mkdir()

    meta = {
        "org_name": "Acme Test Corp",
        "footer_text": "Acme Test Corp \u2022 Test",
        "default_font": "Liberation Sans",
        "heading_font": "Liberation Serif",
    }
    (brand_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (brand_dir / "brand.typ").write_text(
        "// test template\n#set page(paper: \"us-letter\")\n",
        encoding="utf-8",
    )
    (brand_dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    return str(tmp_path)


def _load_brand(brands_dir_path, brand_id):
    """Import renderer with a patched BRANDS_DIR."""
    import app.renderer as renderer
    original = renderer.BRANDS_DIR
    renderer.BRANDS_DIR = brands_dir_path
    try:
        return renderer.load_brand(brand_id)
    finally:
        renderer.BRANDS_DIR = original


def test_load_valid_brand(brands_dir):
    """load_brand returns meta, template, and logo_bytes for a valid brand."""
    result = _load_brand(brands_dir, "acme-test")
    assert result["meta"]["org_name"] == "Acme Test Corp"
    assert "#set page" in result["template"]
    assert result["logo_bytes"] is not None
    assert result["logo_bytes"][:4] == b"\x89PNG"


def test_load_brand_no_logo(brands_dir):
    """load_brand succeeds and returns logo_bytes=None when logo.png absent."""
    os.remove(os.path.join(brands_dir, "acme-test", "logo.png"))
    result = _load_brand(brands_dir, "acme-test")
    assert result["logo_bytes"] is None


def test_load_brand_not_found(brands_dir):
    """load_brand raises ValueError for an unknown brand id."""
    import app.renderer as renderer
    original = renderer.BRANDS_DIR
    renderer.BRANDS_DIR = brands_dir
    try:
        with pytest.raises(ValueError, match="not found"):
            renderer.load_brand("no-such-brand")
    finally:
        renderer.BRANDS_DIR = original


def test_load_brand_missing_meta(brands_dir):
    """load_brand raises FileNotFoundError when meta.json is missing."""
    os.remove(os.path.join(brands_dir, "acme-test", "meta.json"))
    with pytest.raises(FileNotFoundError):
        _load_brand(brands_dir, "acme-test")


def test_load_brand_missing_template(brands_dir):
    """load_brand raises FileNotFoundError when brand.typ is missing."""
    os.remove(os.path.join(brands_dir, "acme-test", "brand.typ"))
    with pytest.raises(FileNotFoundError):
        _load_brand(brands_dir, "acme-test")


def test_load_brand_invalid_json(brands_dir):
    """load_brand raises json.JSONDecodeError for malformed meta.json."""
    import json as json_module
    meta_path = os.path.join(brands_dir, "acme-test", "meta.json")
    with open(meta_path, "w") as f:
        f.write("{not valid json")
    with pytest.raises(json_module.JSONDecodeError):
        _load_brand(brands_dir, "acme-test")
