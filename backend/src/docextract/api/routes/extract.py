"""Invoice extraction endpoint."""

import binascii
import io
import struct
import zlib
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pypdf import PdfReader

from docextract.core.config import get_settings
from docextract.schemas import InvoiceExtractionData
from docextract.services.extractor import (
    ExtractionNotConfiguredError,
    ExtractionProviderError,
    extract_document_data,
)

router = APIRouter(tags=["invoices"])

_EXTENSION_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _detect_mime_type(file_bytes: bytes) -> str | None:
    """Recognize supported formats and reject files with invalid basic structure."""
    if file_bytes.startswith(b"%PDF-"):
        if b"%%EOF" not in file_bytes[-1024:]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PDF is invalid or incomplete.",
            )
        return "application/pdf"

    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        if not _is_valid_png(file_bytes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PNG image is invalid or incomplete.",
            )
        return "image/png"

    if file_bytes.startswith(b"\xff\xd8"):
        if len(file_bytes) < 12 or not file_bytes.endswith(b"\xff\xd9"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded JPEG image is invalid or incomplete.",
            )
        return "image/jpeg"

    return None


def _is_valid_png(file_bytes: bytes) -> bool:
    """Check PNG chunk bounds and CRCs and require image data and an end chunk."""
    offset = 8
    has_header = False
    has_image_data = False
    while offset + 12 <= len(file_bytes):
        chunk_length = struct.unpack(">I", file_bytes[offset : offset + 4])[0]
        chunk_end = offset + 12 + chunk_length
        if chunk_end > len(file_bytes):
            return False

        chunk_type = file_bytes[offset + 4 : offset + 8]
        chunk_data = file_bytes[offset + 8 : offset + 8 + chunk_length]
        chunk_crc = struct.unpack(">I", file_bytes[chunk_end - 4 : chunk_end])[0]
        if binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != chunk_crc:
            return False

        if chunk_type == b"IHDR":
            if has_header or chunk_length != 13:
                return False
            width, height = struct.unpack(">II", chunk_data[:8])
            if width == 0 or height == 0:
                return False
            has_header = True
        elif chunk_type == b"IDAT":
            has_image_data = True
        elif chunk_type == b"IEND":
            if (
                chunk_length != 0
                or chunk_end != len(file_bytes)
                or not has_header
                or not has_image_data
            ):
                return False
            return True

        offset = chunk_end
    return False


def _get_jpeg_dimensions(file_bytes: bytes) -> tuple[int, int] | None:
    """Read JPEG dimensions from a start-of-frame marker without decoding pixels."""
    offset = 2
    while offset < len(file_bytes) - 2:
        if file_bytes[offset] != 0xFF:
            return None
        while offset < len(file_bytes) and file_bytes[offset] == 0xFF:
            offset += 1
        if offset >= len(file_bytes):
            return None
        marker = file_bytes[offset]
        offset += 1
        if marker in {0xD8, 0xD9, 0x01, *range(0xD0, 0xD8)}:
            continue
        if offset + 2 > len(file_bytes):
            return None
        segment_length = struct.unpack(">H", file_bytes[offset : offset + 2])[0]
        segment_end = offset + segment_length
        if segment_length < 2 or segment_end > len(file_bytes):
            return None
        if marker in {
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        }:
            if segment_length < 7:
                return None
            height, width = struct.unpack(">HH", file_bytes[offset + 3 : offset + 7])
            return width, height
        offset = segment_end
    return None


def _get_image_dimensions(file_bytes: bytes, mime_type: str) -> tuple[int, int] | None:
    """Read image dimensions from the encoded header without decoding image pixels."""
    if mime_type == "image/png":
        return struct.unpack(">II", file_bytes[16:24])
    if mime_type == "image/jpeg":
        return _get_jpeg_dimensions(file_bytes)
    return None


def _is_valid_png_image_data(file_bytes: bytes) -> bool:
    """Stream PNG decompression while discarding bounded output chunks."""
    decompressor = zlib.decompressobj()
    offset = 8
    while offset + 12 <= len(file_bytes):
        chunk_length = struct.unpack(">I", file_bytes[offset : offset + 4])[0]
        chunk_end = offset + 12 + chunk_length
        chunk_type = file_bytes[offset + 4 : offset + 8]
        if chunk_type == b"IDAT":
            compressed = file_bytes[offset + 8 : offset + 8 + chunk_length]
            try:
                while compressed:
                    decompressor.decompress(compressed, max_length=64 * 1024)
                    compressed = decompressor.unconsumed_tail
                    if decompressor.unused_data:
                        return False
            except zlib.error:
                return False
        elif chunk_type == b"IEND":
            return decompressor.eof and not decompressor.unused_data
        offset = chunk_end
    return False


def _check_document_resources(file_bytes: bytes, mime_type: str) -> None:
    """Reject documents whose page count or image dimensions exceed configured limits."""
    settings = get_settings()
    if mime_type == "application/pdf":
        try:
            page_count = len(PdfReader(io.BytesIO(file_bytes), strict=True).pages)
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PDF is malformed or cannot be read.",
            ) from error
        if page_count > settings.max_pdf_pages:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"PDF exceeds the maximum of {settings.max_pdf_pages} pages.",
            )
        return

    dimensions = _get_image_dimensions(file_bytes, mime_type)
    if dimensions is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image dimensions could not be read.",
        )
    width, height = dimensions
    if width > settings.max_image_width or height > settings.max_image_height:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                "Image dimensions exceed the maximum of "
                f"{settings.max_image_width} by {settings.max_image_height} pixels."
            ),
        )
    if mime_type == "image/png" and not _is_valid_png_image_data(file_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PNG image data is invalid or incomplete.",
        )


@router.post("/extract", response_model=InvoiceExtractionData)
async def extract_invoice(
    file: Annotated[UploadFile, File(description="An invoice PDF or image file")],
) -> InvoiceExtractionData:
    """Accept an invoice document and return AI-extracted structured data."""
    filename = file.filename or "invoice"
    extension = PurePath(filename).suffix.lower()
    declared_mime_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()

    max_size = get_settings().max_upload_size_bytes
    file_bytes = await file.read(max_size + 1)
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded file exceeds the maximum allowed size.",
        )
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    mime_type = _detect_mime_type(file_bytes)
    if mime_type is None:
        if (
            extension in _EXTENSION_MIME_TYPES
            or declared_mime_type in _EXTENSION_MIME_TYPES.values()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file does not contain valid content for its declared type.",
            )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format. Upload a PDF, JPEG, or PNG file.",
        )
    if extension and extension not in _EXTENSION_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file extension. Upload a PDF, JPEG, or PNG file.",
        )
    if extension and _EXTENSION_MIME_TYPES[extension] != mime_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The filename extension does not match the uploaded file content.",
        )
    if declared_mime_type not in {mime_type, "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The declared MIME type does not match the uploaded file content.",
        )
    if not extension and declared_mime_type != mime_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF, JPEG, or PNG file.",
        )

    _check_document_resources(file_bytes, mime_type)

    try:
        return await extract_document_data(file_bytes, mime_type, filename)
    except ExtractionNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except ExtractionProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invoice extraction failed with all configured AI providers.",
        ) from error
