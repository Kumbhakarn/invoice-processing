"""Invoice business validation behavior and API response tests."""

from fastapi.testclient import TestClient

from docextract.main import app
from docextract.schemas import InvoiceExtractionData, InvoiceLineItem
from docextract.services.invoice_validator import validate_invoice

client = TestClient(app)


def _valid_invoice(**overrides: object) -> InvoiceExtractionData:
    values: dict[str, object] = {
        "invoice_number": "INV-1",
        "invoice_date": "2025-01-15",
        "buyer_name": "Buyer",
        "exporter_name": "Seller",
        "currency": "USD",
        "net_weight": 8,
        "gross_weight": 10,
        "line_items": [
            InvoiceLineItem(
                description_of_goods="Paper",
                quantity=2,
                rate=3,
                amount=6,
                unit_of_measurement="box",
            )
        ],
    }
    values.update(overrides)
    return InvoiceExtractionData.model_validate(values)


def test_consistent_invoice_has_valid_status() -> None:
    result = validate_invoice(_valid_invoice())
    assert result.status == "valid"
    assert result.issues == []


def test_missing_values_and_date_format_are_warnings() -> None:
    result = validate_invoice(
        InvoiceExtractionData(
            invoice_date="15/01/2025",
            line_items=[InvoiceLineItem(quantity=1, amount=4)],
        )
    )
    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.status == "needs_review"
    assert "invoice.date_format" in rule_ids
    assert "invoice.required.invoice_number" in rule_ids
    assert "line_item.description.missing" in rule_ids
    assert "line_item.unit.missing" in rule_ids
    assert all(issue.severity == "warning" for issue in result.issues)


def test_currency_specific_rounding_tolerances_cover_two_zero_and_three_places() -> None:
    for currency, amount in (("USD", 1.00), ("JPY", 10), ("KWD", 1.0)):
        result = validate_invoice(
            _valid_invoice(
                currency=currency,
                line_items=[
                    InvoiceLineItem(
                        description_of_goods="Item",
                        unit_of_measurement="unit",
                        quantity=3,
                        rate=amount / 3,
                        amount=amount,
                    )
                ],
            )
        )
        assert "line_item.amount_reconciliation" not in {
            issue.rule_id for issue in result.issues
        }


def test_discount_or_other_line_adjustment_is_reported_without_rewriting_values() -> None:
    invoice = _valid_invoice(
        line_items=[
            InvoiceLineItem(
                description_of_goods="Item",
                unit_of_measurement="unit",
                quantity=10,
                rate=10,
                amount=90,
            )
        ]
    )
    assert invoice.line_items is not None
    original_amount = invoice.line_items[0].amount
    result = validate_invoice(invoice)
    issue = next(
        issue for issue in result.issues if issue.rule_id == "line_item.amount_reconciliation"
    )
    assert result.status == "needs_review"
    assert "discounts" in issue.message
    assert invoice.line_items[0].amount == original_amount


def test_negative_quantity_and_weight_inconsistency_are_errors() -> None:
    result = validate_invoice(
        _valid_invoice(
            net_weight=12,
            gross_weight=10,
            line_items=[
                InvoiceLineItem(
                    description_of_goods="Item",
                    unit_of_measurement="unit",
                    quantity=-1,
                    rate=-2,
                    amount=-2,
                )
            ],
        )
    )
    assert result.status == "invalid"
    assert {issue.rule_id for issue in result.issues} >= {
        "line_item.quantity.non_negative",
        "line_item.rate.non_negative",
        "invoice.weight_consistency",
    }


def test_currency_shape_is_checked_but_distinct_currencies_are_supported() -> None:
    for code in ("USD", "EUR", "JPY", "KWD"):
        result = validate_invoice(_valid_invoice(currency=code))
        assert "invoice.currency_format" not in {issue.rule_id for issue in result.issues}
    invalid = validate_invoice(_valid_invoice(currency="usd"))
    assert "invoice.currency_format" in {issue.rule_id for issue in invalid.issues}


def test_validation_endpoint_returns_findings_separately_from_invoice_fields() -> None:
    response = client.post(
        "/api/validate",
        json={"invoice_number": "INV-1", "currency": "USD"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_review"
    assert "issues" in payload
    assert "invoice_number" not in payload
