"""Invoice extraction response models."""

from datetime import date as InvoiceDate
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema

InvoiceNumber = Annotated[Decimal, WithJsonSchema({"type": "number"})]


class InvoiceLineItem(BaseModel):
    """A single row from an invoice's line items table."""

    description: str | None = Field(description="Description of the invoiced item")
    quantity: InvoiceNumber | None = Field(description="Quantity billed")
    unit_price: InvoiceNumber | None = Field(description="Price per unit")
    amount: InvoiceNumber | None = Field(description="Total amount for this line")


class InvoiceExtractionResponse(BaseModel):
    """Structured invoice data returned by the extraction endpoint."""

    vendor_name: str | None = Field(description="Name of the vendor or supplier")
    invoice_number: str | None = Field(description="Invoice identifier printed on the document")
    date: InvoiceDate | None = Field(description="Invoice issue date in YYYY-MM-DD format")
    line_items: list[InvoiceLineItem] = Field(description="Rows from the invoice line items table")
    subtotal: InvoiceNumber | None = Field(description="Subtotal before tax")
    tax: InvoiceNumber | None = Field(description="Tax amount")
    total_amount: InvoiceNumber | None = Field(description="Final invoice total")
