"""Invoice extraction endpoint."""

import mimetypes
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from docextract.api.schemas.invoice import InvoiceExtractionResponse
from docextract.services.extraction import (
    ExtractionNotConfiguredError,
    ExtractionProviderError,
    extract_invoice_data,
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


@router.post("/extract", response_model=InvoiceExtractionResponse)
async def extract_invoice(
    file: Annotated[UploadFile, File(description="An invoice PDF or image file")],
) -> InvoiceExtractionResponse:
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

    try:
        return await extract_invoice_data(await file.read(), mime_type, filename)
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
