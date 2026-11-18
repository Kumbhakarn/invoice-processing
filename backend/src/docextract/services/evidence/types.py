"""Shared page and text-box types for field-level evidence processing."""

from dataclasses import dataclass
from typing import Literal

from docextract.schemas_evidence import NormalizedBox


@dataclass(frozen=True, slots=True)
class TextBox:
    """Text and normalized bounds in a one-based page, with top-left origin."""

    page: int
    text: str
    bbox: NormalizedBox
    origin: Literal["top-left"] = "top-left"
    source: Literal["text_layer", "ocr"] = "text_layer"
    ocr_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class DecodedPage:
    """A decoded page ready for text matching or a later OCR stage."""

    page: int
    width: int
    height: int
    text_boxes: tuple[TextBox, ...]
    requires_ocr: bool
    raster_png: bytes | None


@dataclass(frozen=True, slots=True)
class DecodedDocument:
    """Ordered, decoded pages from a supported document."""

    pages: tuple[DecodedPage, ...]
