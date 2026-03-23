# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI application for the md-to-pdf branded document rendering service.

Endpoints
---------
  GET  /healthz                — liveness probe
  GET  /brands                 — list available brand slugs
  GET  /brands/{slug}          — return meta.json for a brand
  POST /brands/{slug}          — create or replace a brand (multipart)
  DELETE /brands/{slug}        — remove a brand
  GET  /brands/{slug}/preview  — render standard preview PDF
  POST /render                 — render Markdown to a branded PDF
"""

import json
import logging
import os
import re
import shutil
import subprocess
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from .models import (
    BrandMetaResponse,
    BrandUploadResponse,
    RenderRequest,
)
from .renderer import (
    BRANDS_DIR,
    PANDOC,
    TYPST,
    remove_brand,
    render_document,
    validate_brand_typ,
)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

#: Slug must be lowercase alphanumeric with internal hyphens.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")

#: Standard preview document used by GET /brands/{slug}/preview.
_PREVIEW_MARKDOWN = """\
# Brand Preview

This document validates the brand configuration is rendering correctly.

## Typography

Standard body text with **bold**, *italic*, and `inline code` formatting.
A second paragraph to check line spacing and measure.

## Table

| Column A     | Column B     | Column C     |
|--------------|--------------|--------------|
| Value Alpha  | Value Beta   | Value Gamma  |
| Value Delta  | Value Epsilon| Value Zeta   |

## Blockquote

> A blockquote for visual style validation.  Good brand templates
> make this distinct from body copy.

## List

- Item one with enough text to verify line wrapping behaviour
- Item two
- Item three

---

*End of brand preview document.*
"""

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="branded-pdf-service",
    summary="Branded Markdown-to-PDF rendering service",
    description=(
        "Accepts Markdown and returns a print-ready branded PDF. "
        "Brand configurations are managed via the brand management API "
        "or pre-loaded from the ``/brands`` volume mount."
    ),
    version="0.2.0",
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate_slug(slug: str) -> None:
    """Raise HTTPException 400 if ``slug`` is not a valid brand slug.

    Args:
        slug: Candidate brand slug string.

    Raises:
        HTTPException: 400 if the slug contains invalid characters or
            reserved names.
    """
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid brand slug '{slug}'. "
                "Slugs must be lowercase alphanumeric with hyphens, "
                "e.g. 'acme-corp'."
            ),
        )


def _list_brand_slugs() -> List[str]:
    """Return sorted list of brand slugs from BRANDS_DIR.

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


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/healthz", summary="Liveness probe")
def health() -> dict:
    """Return service health status and dependency versions."""
    versions: dict = {"status": "ok"}

    # Pandoc version
    try:
        result = subprocess.run(
            [PANDOC, "--version"],
            capture_output=True,
            check=True,
        )
        first_line = result.stdout.decode().splitlines()[0]
        versions["pandoc"] = first_line
    except Exception as exc:  # pragma: no cover
        versions["pandoc"] = f"unavailable: {exc}"

    # Typst version
    try:
        result = subprocess.run(
            [TYPST, "--version"],
            capture_output=True,
            check=True,
        )
        versions["typst"] = result.stdout.decode().strip()
    except Exception as exc:  # pragma: no cover
        versions["typst"] = f"unavailable: {exc}"

    return versions


@app.get(
    "/brands",
    summary="List available brand identifiers",
    response_model=List[str],
)
def list_brands() -> List[str]:
    """Return the names of all brand directories found under BRANDS_DIR.

    Each returned name is a valid ``brand`` slug for ``POST /render`` and
    the brand management endpoints.

    Returns:
        Sorted list of brand slug strings.
    """
    slugs = _list_brand_slugs()
    if not slugs:
        logger.warning("BRANDS_DIR '%s' is empty or missing", BRANDS_DIR)
    return slugs


@app.get(
    "/brands/{slug}",
    summary="Get brand metadata",
    response_model=BrandMetaResponse,
    responses={404: {"description": "Brand not found."}},
)
def get_brand_meta(slug: str) -> BrandMetaResponse:
    """Return the ``meta.json`` for a specific brand.

    Args:
        slug: Brand identifier (sub-directory name under BRANDS_DIR).

    Returns:
        ``BrandMetaResponse`` containing the slug and parsed meta.json.

    Raises:
        HTTPException: 404 if the brand does not exist.
    """
    _validate_slug(slug)
    brand_dir = os.path.join(BRANDS_DIR, slug)
    if not os.path.isdir(brand_dir):
        raise HTTPException(
            status_code=404,
            detail=f"Brand '{slug}' not found.",
        )
    meta_path = os.path.join(brand_dir, "meta.json")
    try:
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Brand '{slug}' has no meta.json.",
        )
    return BrandMetaResponse(slug=slug, meta=meta)


@app.post(
    "/brands/{slug}",
    summary="Create or replace a brand",
    responses={
        200: {"description": "Brand updated."},
        201: {"description": "Brand created."},
        400: {"description": "Invalid input or Typst compile error."},
    },
)
async def upload_brand(
    slug: str,
    meta_json: str = Form(
        ...,
        description="Contents of meta.json as a JSON string.",
    ),
    brand_typ: str = Form(
        ...,
        description="Typst brand template (brand.typ contents).",
    ),
    logo: Optional[UploadFile] = File(
        default=None,
        description="Optional PNG logo file.",
    ),
) -> JSONResponse:
    """Create or replace a brand configuration.

    Accepts a multipart form with the brand template and metadata.
    The Typst template is compiled as a validation step before the brand
    is written to disk; the upload is rejected if compilation fails.

    Args:
        slug: Brand identifier slug.  Must be lowercase alphanumeric
            with optional internal hyphens.
        meta_json: JSON string for ``meta.json`` (org_name, footer_text,
            default_font, heading_font, and any extra fields).
        brand_typ: Full Typst brand template source (``brand.typ``).
        logo: Optional PNG logo upload (``logo.png``).

    Returns:
        ``BrandUploadResponse`` with ``slug`` and ``created`` flag.
        HTTP 201 for a new brand; 200 for an update.

    Raises:
        HTTPException: 400 for invalid slug, malformed JSON, or a
            Typst compile error.
    """
    _validate_slug(slug)

    # Validate meta_json is valid JSON.
    try:
        json.loads(meta_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"meta_json is not valid JSON: {exc}",
        ) from exc

    # Read logo bytes if provided.
    logo_bytes: Optional[bytes] = None
    if logo is not None:
        logo_bytes = await logo.read()
        if not logo_bytes.startswith(b"\x89PNG"):
            raise HTTPException(
                status_code=400,
                detail="logo must be a PNG file (wrong magic bytes).",
            )

    # Validate brand.typ compiles before touching disk.
    try:
        validate_brand_typ(brand_typ, logo_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Write brand files to disk.
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

    if logo_bytes is not None:
        with open(
            os.path.join(brand_dir, "logo.png"), "wb"
        ) as fh:
            fh.write(logo_bytes)
    elif not created:
        # On update, remove stale logo if no new one provided.
        stale_logo = os.path.join(brand_dir, "logo.png")
        if os.path.exists(stale_logo):
            os.remove(stale_logo)

    action = "Created" if created else "Updated"
    logger.info("%s brand '%s'", action, slug)
    payload = BrandUploadResponse(
        slug=slug, created=created
    ).model_dump()
    return JSONResponse(
        status_code=201 if created else 200,
        content=payload,
    )


@app.delete(
    "/brands/{slug}",
    summary="Delete a brand",
    status_code=204,
    responses={
        204: {"description": "Brand deleted."},
        404: {"description": "Brand not found."},
        409: {"description": "Cannot delete the last brand."},
    },
)
def delete_brand(slug: str) -> Response:
    """Remove a brand configuration from the service.

    The last registered brand cannot be deleted (the service requires at
    least one brand to be operational).

    Args:
        slug: Brand identifier to remove.

    Returns:
        HTTP 204 No Content on success.

    Raises:
        HTTPException: 404 if the brand does not exist.
        HTTPException: 409 if deleting would leave no brands.
    """
    _validate_slug(slug)
    all_brands = _list_brand_slugs()

    if slug not in all_brands:
        raise HTTPException(
            status_code=404,
            detail=f"Brand '{slug}' not found.",
        )

    if len(all_brands) <= 1:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete the last registered brand. "
                "The service requires at least one brand."
            ),
        )

    try:
        remove_brand(slug, BRANDS_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)


@app.get(
    "/brands/{slug}/preview",
    summary="Render a brand preview PDF",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Brand preview PDF.",
        },
        404: {"description": "Brand not found."},
        500: {"description": "Rendering error."},
    },
)
def preview_brand(slug: str) -> Response:
    """Render a standard preview document using the specified brand.

    The preview exercises the full rendering pipeline (headings, body
    text, tables, blockquotes, lists) so any brand template issues
    surface immediately.  Useful for validating a newly uploaded brand.

    Args:
        slug: Brand identifier.

    Returns:
        ``application/pdf`` response containing the preview PDF.

    Raises:
        HTTPException: 404 if the brand is not found.
        HTTPException: 500 if rendering fails.
    """
    _validate_slug(slug)
    try:
        pdf_bytes = render_document(
            brand_id=slug,
            sections=[_PREVIEW_MARKDOWN],
            doc_meta={
                "subject": f"Brand Preview — {slug}",
                "status": "PREVIEW",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Preview render failed for '%s': %s", slug, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Preview rendering failed: {exc}",
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{slug}-preview.pdf"'
            )
        },
    )


@app.post(
    "/render",
    summary="Render Markdown to a branded PDF",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Branded PDF document.",
        },
        400: {"description": "Invalid request (unknown brand, bad input)."},
        500: {"description": "Internal rendering error."},
    },
)
def render(request: RenderRequest) -> Response:
    """Render one or more Markdown sections to a single branded PDF.

    The ``markdown`` field accepts either a plain string or a list of
    strings.  When a list is provided each element is rendered as an
    independent page range; the ranges are assembled (in order) into one
    PDF before being returned.

    If ``watermark`` is supplied (e.g. ``"DRAFT"``) the text is stamped
    diagonally across every page of the finished PDF.

    Returns:
        ``application/pdf`` response containing the rendered document.
    """
    sections = (
        [request.markdown]
        if isinstance(request.markdown, str)
        else request.markdown
    )
    doc_meta = request.meta.model_dump() if request.meta else {}

    try:
        pdf_bytes = render_document(
            brand_id=request.brand,
            sections=sections,
            doc_meta=doc_meta,
            watermark=request.watermark,
        )
    except ValueError as exc:
        logger.warning("Render request rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Rendering failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Rendering failed: {exc}",
        ) from exc

    filename = (
        (doc_meta.get("subject") or request.brand).replace(" ", "_")
        + ".pdf"
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )
