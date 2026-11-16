"""Invoice business validation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Body

from docextract.schemas import InvoiceExtractionData
from docextract.schemas_validation import InvoiceValidationResult
from docextract.services.invoice_validator import validate_invoice

router = APIRouter(tags=["invoices"])


@router.post("/validate", response_model=InvoiceValidationResult)
async def validate_extracted_invoice(
    invoice: Annotated[InvoiceExtractionData, Body()],
) -> InvoiceValidationResult:
    """Check business consistency without changing the supplied invoice values."""
    return validate_invoice(invoice)
