"""Nullable Pydantic response models for invoice extraction."""

# Preserve the requested Optional[T] annotations despite Ruff's UP045 preference.
# ruff: noqa: UP045

from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceLineItem(BaseModel):
    """A single goods row from the invoice line items table."""

    model_config = ConfigDict(extra="ignore")

    sr_no: Optional[int] = None
    marks_and_numbers: Optional[str] = None
    number_of_packages: Optional[float] = None
    description_of_goods: Optional[str] = None
    quantity: Optional[float] = None
    hsn_code: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    rate: Optional[float] = None
    amount: Optional[float] = None


class InvoiceExtractionData(BaseModel):
    """Invoice and export document fields requested by the DocExtract workflow."""

    model_config = ConfigDict(extra="ignore")

    document_type: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    exporter_name: Optional[str] = None
    exporter_address: Optional[str] = None
    consignee_name: Optional[str] = None
    consignee_address: Optional[str] = None
    notify_party_name: Optional[str] = None
    notify_party_address: Optional[str] = None
    country_of_origin: Optional[str] = None
    country_of_final_destination: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    final_destination: Optional[str] = None
    shipping_marks: Optional[str] = None
    line_items: Optional[list[InvoiceLineItem]] = None
    currency: Optional[str] = None
    terms_of_delivery_and_payment: Optional[str] = None
    payment_terms: Optional[str] = None
    incoterms: Optional[str] = None
    amount_in_words: Optional[str] = None
    net_weight: Optional[float] = None
    gross_weight: Optional[float] = None
    weight_unit: Optional[str] = None
