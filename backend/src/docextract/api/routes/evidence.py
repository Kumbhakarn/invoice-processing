"""Interim field-level evidence extraction endpoint."""

import logging
import time
from pathlib import PurePath
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Request, UploadFile

from docextract.api.errors import ApiError
from docextract.core.config import get_settings
from docextract.core.request_context import set_file_id
from docextract.schemas_evidence import EvidenceExtractionResponse
from docextract.services.evidence.ocr import (
    OcrEngineUnavailableError,
    OcrTimeoutError,
)
from docextract.services.evidence.pages import DocumentDecodeError
from docextract.services.evidence.pipeline import extract_evidence_document
from docextract.services.extractor import (
    ExtractionNotConfiguredError,
    ExtractionProviderError,
)

router = APIRouter(tags=["invoices"])
logger = logging.getLogger(__name__)

_EXTENSION_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}
_SUPPORTED_MIME_TYPES = frozenset(_EXTENSION_MIME_TYPES.values())


def _detect_mime_type(file_bytes: bytes) -> str | None:
    if file_bytes.startswith(b"%PDF-"):
        if b"%%EOF" not in file_bytes[-1024:]:
            raise ApiError(400, "INVALID_DOCUMENT", "The uploaded document is invalid.")
        return "application/pdf"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if len(file_bytes) >= 12 and file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    if file_bytes.startswith((b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")):
        return "image/tiff"
    return None


@router.post("/extract/evidence", response_model=EvidenceExtractionResponse)
async def extract_invoice_evidence(
    request: Request,
    file: Annotated[UploadFile, File(description="An invoice PDF or image document")],
) -> EvidenceExtractionResponse:
    """Return extraction values with grounded field evidence for review."""
    validation_started = time.perf_counter()
    filename = file.filename or "invoice"
    file_id = str(uuid4())
    request.state.file_id = file_id
    set_file_id(file_id)
    extension = PurePath(filename).suffix.lower()
    declared_mime_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    settings = get_settings()
    file_bytes = await file.read(settings.max_upload_size_bytes + 1)
    request.state.upload_size_bytes = len(file_bytes)
    logger.info(
        "evidence upload received",
        extra={"event": "upload_received", "upload_size_bytes": len(file_bytes)},
    )
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "Uploaded file exceeds the maximum allowed size.")
    if not file_bytes:
        raise ApiError(400, "EMPTY_FILE", "Uploaded file is empty.")

    mime_type = _detect_mime_type(file_bytes)
    if mime_type is None:
        if extension in _EXTENSION_MIME_TYPES or declared_mime_type in _SUPPORTED_MIME_TYPES:
            raise ApiError(400, "INVALID_DOCUMENT", "The uploaded document is invalid.")
        raise ApiError(
            415,
            "UNSUPPORTED_FORMAT",
            "Upload a PDF, JPEG, PNG, WEBP, or TIFF file.",
        )
    if extension and extension not in _EXTENSION_MIME_TYPES:
        raise ApiError(415, "UNSUPPORTED_FORMAT", "The uploaded file format is not supported.")
    if extension and _EXTENSION_MIME_TYPES[extension] != mime_type:
        raise ApiError(415, "UNSUPPORTED_FORMAT", "The file type does not match its content.")
    if declared_mime_type not in {mime_type, "application/octet-stream"}:
        raise ApiError(415, "UNSUPPORTED_FORMAT", "The file type does not match its content.")
    if not extension and declared_mime_type != mime_type:
        raise ApiError(415, "UNSUPPORTED_FORMAT", "The file type does not match its content.")

    validation_ms = round((time.perf_counter() - validation_started) * 1000, 2)
    try:
        return await extract_evidence_document(
            file_bytes,
            mime_type,
            filename,
            settings,
            validation_ms=validation_ms,
        )
    except DocumentDecodeError as error:
        message = str(error)
        if "page count" in message:
            raise ApiError(
                413,
                "DOCUMENT_PAGE_LIMIT_EXCEEDED",
                "Document page limit exceeded.",
            ) from error
        if "dimensions" in message:
            raise ApiError(
                413,
                "IMAGE_DIMENSION_LIMIT_EXCEEDED",
                "Document page dimensions exceed the configured limit.",
            ) from error
        raise ApiError(400, "INVALID_DOCUMENT", "The uploaded document is invalid.") from error
    except OcrTimeoutError as error:
        raise ApiError(504, "OCR_TIMEOUT", "Document OCR timed out.") from error
    except OcrEngineUnavailableError as error:
        raise ApiError(
            503,
            "OCR_ENGINE_UNAVAILABLE",
            "The configured OCR engine is unavailable.",
        ) from error
    except ExtractionNotConfiguredError as error:
        raise ApiError(
            503,
            "MISSING_PROVIDER_CONFIGURATION",
            "No AI extraction provider is configured.",
        ) from error
    except ExtractionProviderError as error:
        provider_errors = {
            "authentication": (
                502,
                "PROVIDER_AUTHENTICATION_FAILURE",
                "AI provider authentication failed.",
            ),
            "rate-limit": (503, "PROVIDER_RATE_LIMIT", "AI provider rate limit reached."),
            "timeout": (504, "PROVIDER_TIMEOUT", "AI provider request timed out."),
            "invalid-response": (
                502,
                "INVALID_AI_RESPONSE",
                "AI provider returned an invalid response.",
            ),
        }
        status_code, code, message = provider_errors.get(
            error.category,
            (502, "PROVIDER_FAILURE", "Invoice extraction failed with configured AI providers."),
        )
        raise ApiError(status_code, code, message) from error
