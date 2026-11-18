"""Tests for mapping invoice extraction data to field-level evidence output."""

import pytest
from pydantic import ValidationError

from docextract.schemas import InvoiceExtractionData, InvoiceLineItem
from docextract.schemas_evidence import (
    DocumentPage,
    EvidenceExtractionResponse,
    EvidenceMetadata,
    FieldEvidence,
    FieldSource,
    ProviderUsageMetadata,
)
from docextract.services.evidence.mapper import map_extraction_fields


def test_mapper_preserves_values_and_maps_evidence_for_top_level_fields() -> None:
    invoice = InvoiceExtractionData(invoice_number="INV-1001", invoice_date="2025-01-15")
    source = FieldSource(
        page=1,
        boxes=[(0.1, 0.2, 0.3, 0.25)],
        status="located",
        reason=None,
        match_count=1,
        evidence_text="Invoice No: INV-1001",
    )

    result = map_extraction_fields(
        invoice,
        [
            FieldEvidence(
                field="invoice_number",
                raw="INV-1001",
                confidence=0.93,
                source=source,
            )
        ],
    )

    assert result["invoice_number"].model_dump() == {
        "value": "INV-1001",
        "raw": "INV-1001",
        "confidence": 0.93,
        "source": source.model_dump(),
        "edited": False,
    }
    assert result["invoice_date"].value == "2025-01-15"
    assert result["invoice_date"].confidence == 0
    assert result["invoice_date"].source.reason == "not_found"
    assert result["buyer_name"].value is None
    assert len(result) == len(InvoiceExtractionData.model_fields) - 1


def test_mapper_tracks_line_item_fields_independently_with_zero_based_paths() -> None:
    invoice = InvoiceExtractionData(
        line_items=[
            InvoiceLineItem(description_of_goods="A4 paper", quantity=10),
            InvoiceLineItem(description_of_goods="Toner", quantity=2),
        ]
    )
    source = FieldSource(
        page=2,
        boxes=[(0.2, 0.4, 0.35, 0.42), (0.2, 0.43, 0.37, 0.45)],
        status="located",
        reason=None,
        match_count=1,
        evidence_text="10 reams of A4 paper",
    )

    result = map_extraction_fields(
        invoice,
        [FieldEvidence(field="line_items[0].description_of_goods", source=source)],
    )

    assert result["line_items[0].description_of_goods"].value == "A4 paper"
    assert result["line_items[0].description_of_goods"].source.page == 2
    assert result["line_items[0].quantity"].value == 10
    assert result["line_items[1].description_of_goods"].value == "Toner"


@pytest.mark.parametrize(
    ("evidence", "message"),
    [
        ([FieldEvidence(field="unknown_field")], "unknown field"),
        (
            [FieldEvidence(field="invoice_number"), FieldEvidence(field="invoice_number")],
            "Duplicate evidence",
        ),
    ],
)
def test_mapper_rejects_unknown_or_duplicate_evidence_paths(
    evidence: list[FieldEvidence], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        map_extraction_fields(InvoiceExtractionData(invoice_number="INV-1"), evidence)


def test_evidence_response_schema_includes_pages_and_provider_reasoning_usage() -> None:
    invoice = InvoiceExtractionData(invoice_number="INV-1")
    fields = map_extraction_fields(invoice, [])
    response = EvidenceExtractionResponse(
        data=invoice,
        fields=fields,
        pages=[DocumentPage(page=1, width=2550, height=3300)],
        meta=EvidenceMetadata(
            timings_ms={"validation": 1.2, "total": 4.5},
            provider_usage=[
                ProviderUsageMetadata(
                    provider="OpenAI",
                    model="example-model",
                    input_tokens=100,
                    output_tokens=20,
                    reasoning_tokens=4,
                )
            ],
        ),
    )

    payload = response.model_dump()
    assert payload["pages"] == [{"page": 1, "width": 2550, "height": 3300}]
    assert payload["meta"]["provider_usage"][0]["reasoning_tokens"] == 4
    assert payload["fields"]["invoice_number"]["value"] == "INV-1"


def test_source_rejects_non_normalized_boxes_and_invalid_location_states() -> None:
    with pytest.raises(ValidationError, match="normalized and ordered"):
        FieldSource(
            page=1,
            boxes=[(-0.1, 0.2, 0.3, 0.25)],
            status="located",
            reason=None,
        )
    with pytest.raises(ValidationError, match="located source requires"):
        FieldSource(page=1, boxes=[], status="located", reason=None)


def test_ambiguous_source_keeps_candidates_without_selecting_a_page() -> None:
    source = FieldSource(
        status="ambiguous",
        reason="ambiguous",
        match_count=2,
        candidates=[
            {"page": 1, "boxes": [(0.1, 0.1, 0.2, 0.12)], "match_score": 0.9},
            {"page": 2, "boxes": [(0.1, 0.1, 0.2, 0.12)], "match_score": 0.88},
        ],
    )
    assert source.page is None
    assert len(source.candidates) == 2
    assert source.reason == "ambiguous"
