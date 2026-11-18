"""Decode document pages and collect digital text before OCR is applied."""

from __future__ import annotations

import io
import re
from typing import Any

import pdfplumber
import pypdfium2 as pdfium  # type: ignore[import-untyped]
from PIL import Image, ImageOps

from docextract.core.config import Settings
from docextract.schemas_evidence import DocumentPage
from docextract.services.evidence.types import DecodedDocument, DecodedPage, TextBox

_SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
_SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "TIFF"}


class DocumentDecodeError(ValueError):
    """Raised when a supported document cannot be safely decoded."""


def decode_document(data: bytes, mime_type: str, settings: Settings) -> DecodedDocument:
    """Decode each PDF/image page, retaining text-layer boxes and OCR rasters."""
    if mime_type == "application/pdf":
        return _decode_pdf(data, settings)
    if mime_type in _SUPPORTED_IMAGE_MIMES:
        return _decode_image(data, settings)
    raise DocumentDecodeError(f"Unsupported evidence document type: {mime_type}")


def _decode_pdf(data: bytes, settings: Settings) -> DecodedDocument:
    pages: list[DecodedPage] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as text_pdf:
            pdf_document = pdfium.PdfDocument(data)
            try:
                page_count = len(text_pdf.pages)
                _check_page_count(page_count, settings.max_pdf_pages)
                if len(pdf_document) != page_count:
                    raise DocumentDecodeError("PDF page decoders disagree on page count")
                for index, text_page in enumerate(text_pdf.pages):
                    page_number = index + 1
                    render_page = pdf_document[index]
                    try:
                        width_points, height_points = render_page.get_size()
                        width = _pixel_size(width_points, settings.evidence_render_dpi)
                        height = _pixel_size(height_points, settings.evidence_render_dpi)
                        _check_dimensions(width, height, settings)
                        words = text_page.extract_words()
                        usable = _has_usable_text(words, settings.evidence_text_layer_min_chars)
                        boxes = tuple(
                            _word_box(
                                word,
                                page_number,
                                float(text_page.width),
                                float(text_page.height),
                            )
                            for word in words
                            if usable
                        )
                        raster = None
                        if not usable:
                            bitmap = render_page.render(scale=settings.evidence_render_dpi / 72)
                            raster = _to_png_bytes(bitmap.to_pil())
                        pages.append(
                            DecodedPage(
                                page=page_number,
                                width=width,
                                height=height,
                                text_boxes=boxes,
                                requires_ocr=not usable,
                                raster_png=raster,
                            )
                        )
                    finally:
                        render_page.close()
            finally:
                pdf_document.close()
    except DocumentDecodeError:
        raise
    except Exception as exc:
        raise DocumentDecodeError("Could not decode PDF document") from exc
    return DecodedDocument(tuple(pages))


def _decode_image(data: bytes, settings: Settings) -> DecodedDocument:
    pages: list[DecodedPage] = []
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in _SUPPORTED_IMAGE_FORMATS:
                raise DocumentDecodeError("Image contents do not match a supported format")
            frame_count = getattr(image, "n_frames", 1)
            _check_page_count(frame_count, settings.max_pdf_pages)
            for index in range(frame_count):
                image.seek(index)
                frame = ImageOps.exif_transpose(image.copy()).convert("RGB")
                width, height = frame.size
                _check_dimensions(width, height, settings)
                pages.append(
                    DecodedPage(
                        page=index + 1,
                        width=width,
                        height=height,
                        text_boxes=(),
                        requires_ocr=True,
                        raster_png=_to_png_bytes(frame),
                    )
                )
    except DocumentDecodeError:
        raise
    except Exception as exc:
        raise DocumentDecodeError("Could not decode image document") from exc
    return DecodedDocument(tuple(pages))


def page_metadata(document: DecodedDocument) -> list[DocumentPage]:
    """Map decoded dimensions to the public page metadata shape."""
    return [
        DocumentPage(page=page.page, width=page.width, height=page.height)
        for page in document.pages
    ]


def _has_usable_text(words: list[dict[str, Any]], minimum_chars: int) -> bool:
    text = "".join(str(word.get("text", "")) for word in words)
    return len(re.sub(r"\s", "", text)) >= minimum_chars


def _word_box(
    word: dict[str, Any], page: int, page_width: float, page_height: float
) -> TextBox:
    text = str(word.get("text", ""))
    x0 = _clamp(float(word["x0"]) / page_width)
    x1 = _clamp(float(word["x1"]) / page_width)
    y0 = _clamp(float(word["top"]) / page_height)
    y1 = _clamp(float(word["bottom"]) / page_height)
    return TextBox(page=page, text=text, bbox=(x0, y0, max(x0, x1), max(y0, y1)))


def _pixel_size(points: float, dpi: int) -> int:
    return max(1, round(points * dpi / 72))


def _check_dimensions(width: int, height: int, settings: Settings) -> None:
    if width > settings.max_image_width or height > settings.max_image_height:
        raise DocumentDecodeError("Decoded page dimensions exceed configured limits")


def _check_page_count(page_count: int, limit: int) -> None:
    if page_count < 1:
        raise DocumentDecodeError("Document has no pages")
    if page_count > limit:
        raise DocumentDecodeError("Document page count exceeds configured limit")


def _to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))
