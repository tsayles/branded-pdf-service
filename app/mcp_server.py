# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
mcp_server.py
─────────────────────────────────────────────────────────────────────────────
MCP (Model Context Protocol) server for branded-pdf-service.

Exposes the same rendering and brand management capabilities as the REST
API as MCP tools, making them discoverable and callable by any
MCP-compatible AI agent (Claude Desktop, LangChain, OpenAI Assistants,
etc.) without the agent needing to construct HTTP requests.

Transport
---------
stdio — the standard MCP transport for local and subprocess deployments.
Works with Claude Desktop and the MCP Inspector tool out of the box.

Authentication
--------------
API key (when PDF_API_KEYS is configured) is read from the
``PDF_API_KEY`` environment variable (singular — the MCP client sets
this in its configuration block).  Set this in the agent's MCP client
config; the server will use it for any write operations.

Usage
-----
::

    python -m app.mcp_server

    # Or in Claude Desktop's mcpServers config:
    {
      "mcpServers": {
        "branded-pdf": {
          "command": "docker",
          "args": ["exec", "-i", "bps", "python", "-m", "app.mcp_server"],
          "env": {
            "PDF_API_KEY": "<your-api-key>"
          }
        }
      }
    }

Tools
-----
- render_pdf       — Markdown → branded PDF (base64)
- list_brands      — list registered brand slugs
- get_brand_meta   — return meta.json for a brand
- upload_brand     — create/replace a brand config
- preview_brand    — render standard preview PDF (base64)
"""

import base64
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .auth import get_valid_keys
from .renderer import (
    BRANDS_DIR,
    load_brand,
    render_document,
    validate_brand_typ,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="branded-pdf-service",
    instructions=(
        "Tools for rendering Markdown to branded, print-ready PDFs and "
        "managing brand configurations. Use render_pdf for document "
        "generation, list_brands to discover available brands, and "
        "upload_brand to register a new brand at runtime."
    ),
)

# ── Auth helper ───────────────────────────────────────────────────────────────


def _check_auth() -> None:
    """Raise RuntimeError if auth is enabled but no key is configured.

    Reads the single-key env var ``PDF_API_KEY`` (as opposed to the
    comma-separated ``PDF_API_KEYS`` used by the REST API).  MCP clients
    supply one key via their config block.

    Raises:
        RuntimeError: When auth is required but no key is set, or when
            the configured key is invalid.
    """
    import secrets as _secrets

    valid_keys = get_valid_keys()
    if not valid_keys:
        return  # Open mode.

    provided = os.environ.get("PDF_API_KEY", "").strip()
    if not provided:
        raise RuntimeError(
            "Authentication required: set PDF_API_KEY in the MCP client "
            "environment config."
        )

    if not any(_secrets.compare_digest(provided, k) for k in valid_keys):
        raise RuntimeError("Invalid PDF_API_KEY.")


# ── MCP Tools ─────────────────────────────────────────────────────────────────


@mcp.tool()
def list_brands() -> List[str]:
    """List all registered brand slugs.

    Returns the names of every brand directory under the brands volume.
    Each returned slug is a valid value for the ``brand`` parameter of
    ``render_pdf``, ``get_brand_meta``, and ``preview_brand``.

    Returns:
        Sorted list of brand slug strings.
    """
    if not os.path.isdir(BRANDS_DIR):
        return []
    return sorted(
        entry.name
        for entry in os.scandir(BRANDS_DIR)
        if entry.is_dir()
    )


@mcp.tool()
def get_brand_meta(brand: str) -> Dict[str, Any]:
    """Return the metadata for a registered brand.

    Args:
        brand: Brand slug (e.g. ``'acme-corp'``).

    Returns:
        Dict containing the brand's meta.json fields (org_name,
        footer_text, default_font, heading_font, and any extras).

    Raises:
        ValueError: If the brand is not found.
    """
    brand_data = load_brand(brand)
    return brand_data["meta"]


@mcp.tool()
def render_pdf(
    brand: str,
    markdown: str,
    title: Optional[str] = None,
    prepared_by: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    watermark: Optional[str] = None,
) -> str:
    """Render Markdown to a branded PDF and return it as base64.

    This is the primary tool for document generation. Provide Markdown
    content and a brand slug; the service runs the full
    Pandoc → Typst → PDF pipeline and returns the PDF bytes encoded as
    base64.

    To decode in Python::

        import base64
        pdf_bytes = base64.b64decode(result)

    Args:
        brand: Brand slug identifying the visual style to apply.
        markdown: Markdown document content.
        title: Optional document subject/title for the meta bar.
        prepared_by: Optional author name for the meta bar.
        date: Optional document date (ISO 8601 recommended).
        status: Optional status label (e.g. ``'DRAFT'``, ``'FINAL'``).
        watermark: Optional diagonal watermark text (e.g. ``'DRAFT'``).

    Returns:
        Base64-encoded PDF bytes (standard alphabet, with padding).

    Raises:
        RuntimeError: If auth is required and PDF_API_KEY is not set or
            invalid.
        ValueError: If the brand is not found or rendering fails.
    """
    _check_auth()
    doc_meta = {}
    if title:
        doc_meta["subject"] = title
    if prepared_by:
        doc_meta["prepared_by"] = prepared_by
    if date:
        doc_meta["date"] = date
    if status:
        doc_meta["status"] = status

    pdf_bytes = render_document(
        brand_id=brand,
        sections=[markdown],
        doc_meta=doc_meta,
        watermark=watermark,
    )
    return base64.b64encode(pdf_bytes).decode("ascii")


@mcp.tool()
def preview_brand(brand: str) -> str:
    """Render a standard preview document for a brand; return base64 PDF.

    Useful for validating a newly uploaded brand configuration.  The
    preview exercises headings, tables, blockquotes, and lists.

    Args:
        brand: Brand slug to preview.

    Returns:
        Base64-encoded PDF bytes.

    Raises:
        RuntimeError: If auth is required and PDF_API_KEY is not set.
        ValueError: If the brand is not found.
    """
    _check_auth()
    _PREVIEW_MD = """\
# Brand Preview

Standard body text with **bold**, *italic*, and `code`.

## Table

| Column A | Column B |
|----------|----------|
| Alpha    | Beta     |
| Delta    | Epsilon  |

> A blockquote for style validation.

- Item one
- Item two
"""
    pdf_bytes = render_document(
        brand_id=brand,
        sections=[_PREVIEW_MD],
        doc_meta={"subject": f"Preview — {brand}", "status": "PREVIEW"},
    )
    return base64.b64encode(pdf_bytes).decode("ascii")


@mcp.tool()
def upload_brand(
    slug: str,
    meta_json: str,
    brand_typ: str,
    logo_png_base64: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or replace a brand configuration.

    The Typst template is compiled before being saved. The upload is
    rejected if the template produces a compile error.

    Args:
        slug: Brand slug (lowercase alphanumeric with hyphens).
        meta_json: JSON string for ``meta.json``.  Required fields:
            ``org_name``, ``footer_text``, ``default_font``,
            ``heading_font``.
        brand_typ: Full Typst brand template source.
        logo_png_base64: Optional base64-encoded PNG logo bytes.

    Returns:
        Dict with ``slug`` and ``created`` (True for new brand, False
        for update).

    Raises:
        RuntimeError: If auth is required and PDF_API_KEY is not set.
        ValueError: If meta_json is invalid JSON or brand_typ fails to
            compile.
    """
    _check_auth()

    import re as _re
    import shutil as _shutil

    _SLUG_RE = _re.compile(
        r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$"
    )
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug '{slug}'. Use lowercase alphanumeric + hyphens."
        )

    try:
        json.loads(meta_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"meta_json is not valid JSON: {exc}") from exc

    logo_bytes: Optional[bytes] = None
    if logo_png_base64:
        logo_bytes = base64.b64decode(logo_png_base64)
        if not logo_bytes.startswith(b"\x89PNG"):
            raise ValueError("logo_png_base64 must be a PNG file.")

    validate_brand_typ(brand_typ, logo_bytes)

    brand_dir = os.path.join(BRANDS_DIR, slug)
    created = not os.path.isdir(brand_dir)
    os.makedirs(brand_dir, exist_ok=True)

    with open(
        os.path.join(brand_dir, "meta.json"), "w", encoding="utf-8"
    ) as fh:
        fh.write(meta_json)
    with open(
        os.path.join(brand_dir, "brand.typ"), "w", encoding="utf-8"
    ) as fh:
        fh.write(brand_typ)
    if logo_bytes:
        with open(
            os.path.join(brand_dir, "logo.png"), "wb"
        ) as fh:
            fh.write(logo_bytes)
    elif not created:
        stale = os.path.join(brand_dir, "logo.png")
        if os.path.exists(stale):
            os.remove(stale)

    logger.info(
        "%s brand '%s' via MCP", "Created" if created else "Updated", slug
    )
    return {"slug": slug, "created": created}


def main() -> None:
    """Entry point: start the MCP server on stdio transport."""
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
