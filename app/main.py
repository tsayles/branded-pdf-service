"""
main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI application for the md-to-pdf branded document rendering service.

Endpoints
---------
  GET  /health      — liveness probe
  GET  /brands      — list available brand identifiers
  POST /render      — render Markdown to a branded PDF
"""

import logging
import os
import subprocess
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from .models import RenderRequest
from .renderer import BRANDS_DIR, PANDOC, TYPST, render_document

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="md-to-pdf",
    summary="Branded Markdown-to-PDF rendering service",
    description=(
        "Accepts Markdown and returns a print-ready branded PDF. "
        "Brand configurations are loaded from the ``/brands`` volume mount."
    ),
    version="1.0.0",
)


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", summary="Liveness probe")
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
    """Return the names of all brand directories found under the brands volume.

    Each returned name is a valid value for the ``brand`` field in a
    ``POST /render`` request.
    """
    if not os.path.isdir(BRANDS_DIR):
        logger.warning("BRANDS_DIR '%s' does not exist", BRANDS_DIR)
        return []
    return sorted(
        entry.name
        for entry in os.scandir(BRANDS_DIR)
        if entry.is_dir()
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

    The ``markdown`` field accepts either a plain string or a list of strings.
    When a list is provided each element is rendered as an independent page
    range; the ranges are assembled (in order) into one PDF before being
    returned.

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
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
