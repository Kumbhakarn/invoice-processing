"""Invoice extraction endpoint."""

import binascii
import struct
import zlib
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

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
    """Check PNG chunk bounds and CRCs, and verify its compressed image data."""
    offset = 8
    has_header = False
    image_data: list[bytes] = []
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
            image_data.append(chunk_data)
        elif chunk_type == b"IEND":
            if (
                chunk_length != 0
                or chunk_end != len(file_bytes)
                or not has_header
                or not image_data
            ):
                return False
            try:
                return bool(zlib.decompress(b"".join(image_data)))
            except zlib.error:
                return False

        offset = chunk_end
    return False


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
