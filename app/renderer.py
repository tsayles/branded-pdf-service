# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
renderer.py
─────────────────────────────────────────────────────────────────────────────
Core PDF rendering pipeline for the md-to-pdf service.

Pipeline
--------
  Pandoc          -> Typst body  (robust Markdown parser; --to typst)
  build_typst()   -> full .typ   (brand template + meta block + body)
  typst compile   -> PDF         (single self-contained binary; no deps)
  reportlab       -> watermark   (diagonal text overlay PDF)
  pypdf           -> stamp       (merge watermark into content PDF)
  pypdf           -> assemble    (concatenate multi-section PDFs)

Design notes
------------
- Typst resolves asset paths (e.g. logo.png) relative to the .typ source
  file; logo.png is copied into the compile temp-dir if present.
- Pandoc 3.x is required for ``--to typst`` output support.
- No file:// resource restrictions, no shm requirements, no polling —
  ``typst compile`` writes the PDF synchronously and exits when done.
"""

import io
import json
import logging
import os
import subprocess
import tempfile
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# ── Runtime-configurable paths ────────────────────────────────────────────────

BRANDS_DIR = os.environ.get("BRANDS_DIR", "/brands")
PANDOC = os.environ.get("PANDOC_PATH", "/usr/local/bin/pandoc")
TYPST = os.environ.get("TYPST_PATH", "/usr/local/bin/typst")


# ── Brand loading ─────────────────────────────────────────────────────────────


def load_brand(brand_id: str) -> Dict:
    """Load brand configuration from the brands directory.

    Expects the following layout under ``BRANDS_DIR/<brand_id>/``::

        meta.json   — organisation name, footer text, etc.
        brand.typ   — Typst brand template (page setup, heading styles …)
        logo.png    — optional organisation logo

    The logo bytes (if present) are read into memory so the renderer can
    copy them into each Typst compile directory, where Typst resolves
    asset paths relative to the source file.

    Args:
        brand_id: Sub-directory name under ``BRANDS_DIR``.

    Returns:
        Dict with keys ``meta`` (dict), ``template`` (str),
        ``logo_bytes`` (bytes | None).

    Raises:
        ValueError: If the brand directory does not exist.
        FileNotFoundError: If ``meta.json`` or ``brand.typ`` are missing.
    """
    brand_dir = os.path.join(BRANDS_DIR, brand_id)
    if not os.path.isdir(brand_dir):
        raise ValueError(
            f"Brand '{brand_id}' not found at {brand_dir}"
        )

    meta_path = os.path.join(brand_dir, "meta.json")
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    typ_path = os.path.join(brand_dir, "brand.typ")
    with open(typ_path, encoding="utf-8") as fh:
        template = fh.read()

    logo_bytes: Optional[bytes] = None
    logo_path = os.path.join(brand_dir, "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as fh:
            logo_bytes = fh.read()
        logger.debug(
            "Loaded logo for brand '%s' (%d bytes)",
            brand_id, len(logo_bytes),
        )
    else:
        logger.debug("No logo.png for brand '%s'", brand_id)

    return {
        "meta": meta,
        "template": template,
        "logo_bytes": logo_bytes,
    }


# ── Markdown → Typst conversion ───────────────────────────────────────────────


def pandoc_to_typst(markdown: str) -> str:
    """Convert Markdown to a Typst body fragment using Pandoc.

    Uses ``pandoc --from markdown+smart --to typst`` (non-standalone) to
    produce a Typst content fragment.  Pandoc 3.x or later is required
    for Typst output support.

    Args:
        markdown: Markdown source text.

    Returns:
        Typst fragment string (headings, paragraphs, lists … without a
        page-setup preamble).

    Raises:
        subprocess.CalledProcessError: If Pandoc exits with a non-zero
            status.
    """
    result = subprocess.run(
        [PANDOC, "--from=markdown+smart", "--to=typst"],
        input=markdown.encode(),
        capture_output=True,
        check=True,
    )
    return result.stdout.decode()


# ── Typst document assembly ───────────────────────────────────────────────────


def _escape_typst(text: str) -> str:
    """Escape special Typst markup characters in plain text.

    Args:
        text: Plain-text string to escape.

    Returns:
        String safe for inclusion inside Typst content mode (``[...]``).
    """
    # Backslash must be escaped first to avoid double-escaping.
    for char in "\\#@*_`<>[]{}":
        text = text.replace(char, f"\\{char}")
    return text


def _meta_block_typst(doc_meta: Dict) -> str:
    """Build a Typst markup block for document metadata.

    Renders ``prepared_by``, ``date``, ``subject``, and ``status`` as a
    two-column grid inside a lightly-styled box.  Returns an empty string
    if no fields are present.

    Args:
        doc_meta: Document metadata dict.

    Returns:
        Typst markup string or ``''``.
    """
    pairs = []
    for label, key in [
        ("Prepared by", "prepared_by"),
        ("Date", "date"),
        ("Subject", "subject"),
        ("Status", "status"),
    ]:
        value = doc_meta.get(key)
        if value:
            pairs.append((label, _escape_typst(str(value))))

    if not pairs:
        return ""

    cells = [f"[*{lbl}:* {val}]" for lbl, val in pairs]
    # Pad to an even count for the 2-column grid.
    if len(cells) % 2:
        cells.append("[]")
    cells_str = ", ".join(cells)

    return (
        "#block(\n"
        "  fill: rgb(\"#f5f5f5\"),\n"
        "  inset: (x: 8pt, y: 6pt),\n"
        "  width: 100%,\n"
        "  radius: 2pt,\n"
        "  stroke: 0.5pt + rgb(\"#cccccc\"),\n"
        ")[\n"
        "  #set text(size: 9pt)\n"
        f"  #grid(columns: (1fr, 1fr), row-gutter: 4pt, {cells_str})\n"
        "]\n"
        "#v(8pt)"
    )


def build_typst(
    typst_body: str,
    brand: Dict,
    doc_meta: Dict,
) -> str:
    """Assemble the full branded Typst document.

    Concatenates (in order): brand template → meta block → Pandoc body.

    Args:
        typst_body: Typst fragment produced by Pandoc.
        brand: Brand dict returned by :func:`load_brand`.
        doc_meta: Document metadata dict.

    Returns:
        Complete Typst source string ready for ``typst compile``.
    """
    parts = [brand["template"]]
    meta_block = _meta_block_typst(doc_meta)
    if meta_block:
        parts.append(meta_block)
    parts.append(typst_body)
    return "\n\n".join(parts)


# ── Typst compilation ─────────────────────────────────────────────────────────


def compile_typst(
    typst_source: str,
    brand: Dict,
    output_path: str,
) -> None:
    """Compile a Typst source document to a PDF file.

    Writes the source to a temporary directory alongside ``logo.png``
    (if the brand provides one), then runs ``typst compile``.  Typst
    resolves asset paths relative to the source file, so the logo must
    be in the same directory as the ``.typ`` file.

    Args:
        typst_source: Full Typst document source.
        brand: Brand dict returned by :func:`load_brand`.
        output_path: Destination PDF path (absolute or relative to CWD).

    Raises:
        subprocess.CalledProcessError: If ``typst compile`` exits non-zero.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        typ_path = os.path.join(tmpdir, "document.typ")
        with open(typ_path, "w", encoding="utf-8") as fh:
            fh.write(typst_source)

        if brand.get("logo_bytes"):
            with open(
                os.path.join(tmpdir, "logo.png"), "wb"
            ) as fh:
                fh.write(brand["logo_bytes"])

        abs_output = os.path.abspath(output_path)
        logger.debug(
            "typst compile: %s -> %s", typ_path, abs_output
        )
        subprocess.run(
            [TYPST, "compile", typ_path, abs_output],
            check=True,
            capture_output=True,
            cwd=tmpdir,
        )


# ── Watermark generation & stamping ──────────────────────────────────────────


def _create_watermark_pdf(text: str) -> bytes:
    """Generate a single-page watermark PDF with diagonal text.

    Uses reportlab to render ``text`` at 45° across a letter-sized page
    at 40 % opacity.  The resulting PDF is intended to be stamped onto
    content pages via :func:`_apply_watermark`.

    Args:
        text: Watermark text (e.g. ``'DRAFT'``).

    Returns:
        PDF bytes for the single watermark page.
    """
    buf = io.BytesIO()
    width, height = letter
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 90)
    c.setFillColorRGB(0.7, 0.7, 0.7, alpha=0.40)
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    return buf.getvalue()


def _apply_watermark(pdf_bytes: bytes, watermark_bytes: bytes) -> bytes:
    """Stamp a watermark PDF onto every page of a content PDF.

    Args:
        pdf_bytes: Content PDF bytes.
        watermark_bytes: Single-page watermark PDF bytes.

    Returns:
        Stamped PDF bytes.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    wm_reader = PdfReader(io.BytesIO(watermark_bytes))
    wm_page = wm_reader.pages[0]

    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ── Multi-section PDF assembly ────────────────────────────────────────────────


def _assemble_pdfs(pdf_bytes_list: List[bytes]) -> bytes:
    """Concatenate multiple PDF byte strings into a single PDF.

    Args:
        pdf_bytes_list: Ordered list of PDF byte strings.

    Returns:
        Merged PDF bytes.
    """
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ── Public rendering entry point ──────────────────────────────────────────────


def render_document(
    brand_id: str,
    sections: List[str],
    doc_meta: Optional[Dict] = None,
    watermark: Optional[str] = None,
) -> bytes:
    """Render a branded PDF document from one or more Markdown sections.

    Each section in ``sections`` is independently converted through the
    full pipeline (Pandoc → Typst → typst compile → PDF).  If more than
    one section is provided the resulting PDFs are assembled (in order)
    into a single document.  If ``watermark`` is supplied the text is
    stamped diagonally across every page before assembly.

    Args:
        brand_id: Brand identifier (must exist under ``BRANDS_DIR``).
        sections: List of Markdown strings.  Minimum one element.
        doc_meta: Optional document metadata dict.
        watermark: Optional diagonal watermark text.

    Returns:
        PDF bytes for the finished document.

    Raises:
        ValueError: If the brand is not found.
        subprocess.CalledProcessError: If Pandoc or Typst fails.
    """
    if doc_meta is None:
        doc_meta = {}

    logger.info(
        "Rendering: brand=%s, sections=%d, watermark=%s",
        brand_id, len(sections), repr(watermark),
    )

    brand = load_brand(brand_id)
    watermark_bytes: Optional[bytes] = (
        _create_watermark_pdf(watermark) if watermark else None
    )

    section_pdfs: List[bytes] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, markdown in enumerate(sections):
            logger.debug(
                "Processing section %d/%d", idx + 1, len(sections)
            )
            typst_body = pandoc_to_typst(markdown)
            typst_source = build_typst(typst_body, brand, doc_meta)
            pdf_path = os.path.join(
                tmpdir, f"section_{idx:03d}.pdf"
            )
            compile_typst(typst_source, brand, pdf_path)
            with open(pdf_path, "rb") as fh:
                section_pdfs.append(fh.read())

    if watermark_bytes:
        section_pdfs = [
            _apply_watermark(p, watermark_bytes) for p in section_pdfs
        ]

    if len(section_pdfs) == 1:
        result = section_pdfs[0]
    else:
        result = _assemble_pdfs(section_pdfs)

    logger.info(
        "Rendered successfully: %d bytes, %d section(s)",
        len(result), len(sections),
    )
    return result
