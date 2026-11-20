"""Invoice business validation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Body

from docextract.api.errors import ApiErrorResponse
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_validation import InvoiceValidationResult
from docextract.services.invoice_validator import validate_invoice

router = APIRouter(tags=["invoices"])


@router.post(
    "/validate",
    response_model=InvoiceValidationResult,
    summary="Validate extracted invoice data",
    description=(
        "Check business consistency for an InvoiceExtractionData JSON body. "
        "This endpoint does not call an AI provider or alter the supplied values."
    ),
    response_description="Validation status and any non-mutating business findings.",
    responses={
        422: {
            "model": ApiErrorResponse,
            "description": "The JSON body does not match the invoice schema.",
        },
        500: {"model": ApiErrorResponse, "description": "Unexpected server error."},
    },
)
async def validate_extracted_invoice(
    invoice: Annotated[InvoiceExtractionData, Body()],
) -> InvoiceValidationResult:
    """Check business consistency without changing the supplied invoice values."""
    return validate_invoice(invoice)
