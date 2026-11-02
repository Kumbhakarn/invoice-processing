"""Invoice extraction endpoint."""

import mimetypes
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

_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"}


def _is_supported_file(file: UploadFile) -> bool:
    """Accept PDFs and common image formats based on MIME type or filename."""
    content_type = (file.content_type or "").lower()
    extension = PurePath(file.filename or "").suffix.lower()
    return (
        content_type == "application/pdf"
        or content_type.startswith("image/")
        or extension == ".pdf"
        or extension in _ALLOWED_IMAGE_EXTENSIONS
    )


@router.post("/extract", response_model=InvoiceExtractionData)
async def extract_invoice(
    file: Annotated[UploadFile, File(description="An invoice PDF or image file")],
) -> InvoiceExtractionData:
    """Accept an invoice document and return AI-extracted structured data."""
    if not _is_supported_file(file):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF or image file.",
        )

    filename = file.filename or "invoice"
    mime_type = file.content_type or mimetypes.guess_type(filename)[0] or ""
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(filename)[0] or mime_type

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
