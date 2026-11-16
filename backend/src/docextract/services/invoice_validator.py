"""Business checks for the fields available in the extraction schema."""

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from docextract.schemas import InvoiceExtractionData
from docextract.schemas_validation import InvoiceValidationResult, ValidationIssue

# ISO 4217 currencies with non-default minor units. Other currency codes use two places.
_ZERO_DECIMAL_CURRENCIES = frozenset(
    "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF".split()
)
_THREE_DECIMAL_CURRENCIES = frozenset("BHD IQD JOD KWD LYD OMR TND".split())


def _money_tolerance(currency: str | None) -> Decimal:
    if currency in _ZERO_DECIMAL_CURRENCIES:
        places = 0
    elif currency in _THREE_DECIMAL_CURRENCIES:
        places = 3
    else:
        places = 2
    return Decimal("0.5") * (Decimal(10) ** -places)


def validate_invoice(invoice: InvoiceExtractionData) -> InvoiceValidationResult:
    """Return findings without changing or replacing any extracted value."""
    issues: list[ValidationIssue] = []

    def add(
        rule_id: str,
        field: str,
        severity: Literal["warning", "error"],
        message: str,
        line_item_index: int | None = None,
    ) -> None:
        issues.append(
            ValidationIssue(
                rule_id=rule_id,
                field=field,
                line_item_index=line_item_index,
                severity=severity,
                message=message,
            )
        )

    required_fields = {
        "invoice_number": "Invoice number was not extracted.",
        "invoice_date": "Invoice date was not extracted.",
        "buyer_name": "Buyer name was not extracted.",
        "exporter_name": "Exporter name was not extracted.",
        "currency": "Currency was not extracted.",
    }
    for field, message in required_fields.items():
        value = getattr(invoice, field)
        if value is None or not value.strip():
            add(f"invoice.required.{field}", field, "warning", message)

    if invoice.invoice_date and invoice.invoice_date.strip():
        try:
            date_text = invoice.invoice_date.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text) is None:
                raise ValueError("date is not ISO YYYY-MM-DD")
            date.fromisoformat(date_text)
        except ValueError:
            add(
                "invoice.date_format",
                "invoice_date",
                "warning",
                "Invoice date is not in ISO YYYY-MM-DD format; review the extracted date.",
            )

    if invoice.currency and invoice.currency.strip():
        if re.fullmatch(r"[A-Z]{3}", invoice.currency.strip()) is None:
            add(
                "invoice.currency_format",
                "currency",
                "warning",
                "Currency is not a three-letter uppercase code; review the extracted value.",
            )

    for field, value in (
        ("net_weight", invoice.net_weight),
        ("gross_weight", invoice.gross_weight),
    ):
        if value is not None and value < 0:
            add(
                f"invoice.{field}.non_negative",
                field,
                "error",
                f"{field.replace('_', ' ').capitalize()} cannot be negative.",
            )
    if (
        invoice.net_weight is not None
        and invoice.gross_weight is not None
        and invoice.net_weight >= 0
        and invoice.gross_weight >= 0
        and invoice.gross_weight < invoice.net_weight
    ):
        add(
            "invoice.weight_consistency",
            "gross_weight",
            "error",
            "Gross weight is lower than net weight; review both extracted weights.",
        )

    for index, item in enumerate(invoice.line_items or [], start=1):
        prefix = f"line_items[{index - 1}]"
        if item.description_of_goods is None or not item.description_of_goods.strip():
            add(
                "line_item.description.missing",
                f"{prefix}.description_of_goods",
                "warning",
                "Line item description was not extracted.",
                index,
            )
        if (
            (item.quantity is not None or item.rate is not None or item.amount is not None)
            and (item.unit_of_measurement is None or not item.unit_of_measurement.strip())
        ):
            add(
                "line_item.unit.missing",
                f"{prefix}.unit_of_measurement",
                "warning",
                "Line item unit of measurement was not extracted.",
                index,
            )
        if item.quantity is not None and item.quantity < 0:
            add(
                "line_item.quantity.non_negative",
                f"{prefix}.quantity",
                "error",
                "Line item quantity is negative; review the extracted value.",
                index,
            )
        if item.rate is not None and item.rate < 0:
            add(
                "line_item.rate.non_negative",
                f"{prefix}.rate",
                "error",
                "Line item rate is negative; review the extracted value.",
                index,
            )
        if item.quantity is not None and item.rate is not None and item.amount is not None:
            calculated = Decimal(str(item.quantity)) * Decimal(str(item.rate))
            amount = Decimal(str(item.amount))
            if abs(calculated - amount) > _money_tolerance(invoice.currency):
                add(
                    "line_item.amount_reconciliation",
                    f"{prefix}.amount",
                    "warning",
                    "Quantity multiplied by rate differs from the line amount beyond currency "
                    "rounding tolerance; discounts, conversions, or other adjustments may explain "
                    "the difference.",
                    index,
                )

    has_errors = any(issue.severity == "error" for issue in issues)
    status: Literal["valid", "needs_review", "invalid"] = (
        "invalid" if has_errors else "needs_review" if issues else "valid"
    )
    return InvoiceValidationResult(status=status, issues=issues)
