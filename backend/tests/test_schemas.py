"""Tests for nullable invoice extraction schema and serialization behavior."""

import pytest
from pydantic import ValidationError

from docextract.schemas import InvoiceExtractionData, InvoiceLineItem


def test_every_top_level_schema_field_is_nullable() -> None:
    result = InvoiceExtractionData()

    assert set(result.model_fields_set) == set()
    assert all(value is None for value in result.model_dump().values())
    assert set(result.model_dump()) == set(InvoiceExtractionData.model_fields)


def test_optional_fields_can_be_omitted_or_explicitly_null() -> None:
    omitted = InvoiceExtractionData()
    explicit = InvoiceExtractionData(invoice_number=None, buyer_name=None, line_items=None)

    assert omitted.invoice_number is None
    assert explicit.invoice_number is None
    assert explicit.model_fields_set == {"invoice_number", "buyer_name", "line_items"}


@pytest.mark.parametrize(
    "payload",
    [
        {"invoice_number": 123},
        {"line_items": {"description_of_goods": "Paper"}},
        {"line_items": [{"quantity": "not-a-number"}]},
    ],
)
def test_incorrect_field_types_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        InvoiceExtractionData.model_validate(payload)


def test_extra_fields_are_ignored() -> None:
    result = InvoiceExtractionData.model_validate(
        {"invoice_number": "INV-12", "unexpected": "ignored"}
    )

    assert result.invoice_number == "INV-12"
    assert "unexpected" not in result.model_dump()


def test_nested_line_items_validate_all_nullable_fields() -> None:
    result = InvoiceExtractionData.model_validate(
        {
            "line_items": [
                {"sr_no": 1, "description_of_goods": "Paper", "quantity": 2},
                {"description_of_goods": None, "quantity": None},
            ]
        }
    )

    assert len(result.line_items or []) == 2
    assert result.line_items[0].description_of_goods == "Paper"
    assert all(value is None for value in result.line_items[1].model_dump().values())
    assert set(result.line_items[0].model_dump()) == set(InvoiceLineItem.model_fields)


def test_serialization_round_trip_preserves_explicit_nulls_and_nested_data() -> None:
    original = InvoiceExtractionData(
        invoice_number="INV-99",
        buyer_name=None,
        line_items=[InvoiceLineItem(sr_no=1, amount=12.5)],
    )

    restored = InvoiceExtractionData.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.model_dump() == original.model_dump()
