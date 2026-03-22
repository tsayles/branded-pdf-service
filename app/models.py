"""
models.py
─────────────────────────────────────────────────────────────────────────────
Pydantic request / response models for the md-to-pdf service.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class DocMeta(BaseModel):
    """Document-level metadata injected into the branded header / meta bar."""

    prepared_by: Optional[str] = Field(
        default=None, description="Author or originating body."
    )
    date: Optional[str] = Field(
        default=None, description="Document date (ISO 8601 preferred)."
    )
    subject: Optional[str] = Field(
        default=None, description="Document subject / title."
    )
    status: Optional[str] = Field(
        default=None,
        description="Document status label (e.g. DRAFT, FINAL).",
    )


class RenderRequest(BaseModel):
    """
    Request body for POST /render.

    ``markdown`` may be a single Markdown string **or** a list of Markdown
    strings.  When a list is supplied each element is rendered as an
    independent PDF section; the sections are assembled (in order) into a
    single PDF before being returned.
    """

    brand: str = Field(
        ...,
        description=(
            "Brand identifier. Must match a sub-directory name under the "
            "configured brands volume (e.g. 'greencrest-villa')."
        ),
    )
    markdown: Union[str, List[str]] = Field(
        ...,
        description=(
            "Markdown content.  Provide a single string or a list of strings "
            "for multi-section documents."
        ),
    )
    meta: Optional[DocMeta] = Field(
        default=None,
        description="Optional document metadata for the branded meta bar.",
    )
    watermark: Optional[str] = Field(
        default=None,
        description=(
            "Optional diagonal watermark text (e.g. 'DRAFT').  Applied to "
            "every page of the finished PDF."
        ),
    )
