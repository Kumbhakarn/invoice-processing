"""Evidence matching tests use known word and OCR line boxes."""

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData, InvoiceLineItem
from docextract.services.evidence.matcher import match_invoice_fields
from docextract.services.evidence.types import TextBox


def _box(
    text: str,
    x: float,
    y: float,
    *,
    page: int = 1,
    source: str = "text_layer",
) -> TextBox:
    return TextBox(
        page=page,
        text=text,
        bbox=(x, y, x + 0.05, y + 0.01),
        source=source,  # type: ignore[arg-type]
        ocr_confidence=0.9 if source == "ocr" else None,
    )


def _source(
    data: InvoiceExtractionData,
    field: str,
    boxes: list[TextBox],
    *,
    ocr_failed: bool = False,
    **settings_kwargs: object,
):
    evidence = match_invoice_fields(
        data,
        boxes,
        Settings(**settings_kwargs),
        ocr_failed=ocr_failed,
    )
    return next(item.source for item in evidence if item.field == field)


def test_exact_text_layer_match_returns_real_box_and_document_quote() -> None:
    source = _source(
        InvoiceExtractionData(invoice_number="INV-1001"),
        "invoice_number",
        [_box("Invoice", 0.1, 0.1), _box("No:", 0.17, 0.1), _box("INV-1001", 0.25, 0.1)],
    )

    assert source.status == "located"
    assert source.page == 1
    assert source.evidence_text == "INV-1001"
    assert source.estimated is False
    assert source.match_count == 1


def test_date_and_decimal_normalization() -> None:
    date_source = _source(
        InvoiceExtractionData(invoice_date="2026-01-15"),
        "invoice_date",
        [
            _box("Invoice", 0.1, 0.1),
            _box("Date:", 0.18, 0.1),
            _box("15", 0.27, 0.1),
            _box("Jan", 0.31, 0.1),
            _box("2026", 0.36, 0.1),
        ],
    )
    amount_source = _source(
        InvoiceExtractionData(line_items=[InvoiceLineItem(amount=1000.0)]),
        "line_items[0].amount",
        [_box("1,000.00", 0.5, 0.4)],
    )

    assert date_source.status == "located"
    assert date_source.evidence_text == "15 Jan 2026"
    assert amount_source.status == "located"


def test_ocr_confusions_and_whitespace_normalize_and_subline_box_is_marked() -> None:
    source = _source(
        InvoiceExtractionData(invoice_number="INV-1001"),
        "invoice_number",
        [_box("Invoice   No: INV-I001 issued", 0.1, 0.1, source="ocr")],
    )

    assert source.status == "located"
    assert source.estimated is True
    assert source.boxes[0][0] > 0.1
    assert source.boxes[0][2] < 0.9
    assert source.candidates[0].estimated is True


def test_ocr_numeric_matching_handles_group_separators_and_decimal_comma() -> None:
    grouped = _source(
        InvoiceExtractionData(line_items=[InvoiceLineItem(amount=1000.0)]),
        "line_items[0].amount",
        [_box("Total 1,000.00 USD", 0.1, 0.1, source="ocr")],
    )
    decimal_comma = _source(
        InvoiceExtractionData(line_items=[InvoiceLineItem(rate=1.5)]),
        "line_items[0].rate",
        [_box("1,50", 0.5, 0.4, source="ocr")],
    )

    assert grouped.status == "located"
    assert decimal_comma.status == "located"


def test_multiline_address_returns_one_box_for_each_line() -> None:
    source = _source(
        InvoiceExtractionData(buyer_address="1 Example Street Example City"),
        "buyer_address",
        [
            _box("1", 0.1, 0.1),
            _box("Example", 0.16, 0.1),
            _box("Street", 0.25, 0.1),
            _box("Example", 0.1, 0.12),
            _box("City", 0.19, 0.12),
        ],
    )

    assert source.status == "located"
    assert len(source.boxes) == 5
    assert len({box[1] for box in source.boxes}) == 2


def test_ambiguous_repeated_currency_values_return_every_candidate() -> None:
    source = _source(
        InvoiceExtractionData(currency="USD"),
        "currency",
        [_box("USD", 0.1, 0.1), _box("USD", 0.7, 0.8, page=2)],
    )

    assert source.status == "ambiguous"
    assert source.reason == "ambiguous"
    assert source.match_count == 2
    assert {candidate.page for candidate in source.candidates} == {1, 2}


def test_nearest_label_can_disambiguate_repeated_top_level_values() -> None:
    source = _source(
        InvoiceExtractionData(invoice_number="INV-1"),
        "invoice_number",
        [
            _box("Invoice", 0.1, 0.1),
            _box("No:", 0.18, 0.1),
            _box("INV-1", 0.24, 0.1),
            _box("Reference", 0.1, 0.4),
            _box("INV-1", 0.22, 0.4),
        ],
    )

    assert source.status == "located"
    assert source.boxes[0][1] == 0.1
    assert source.match_count == 2


def test_line_item_same_row_context_selects_the_matching_quantity() -> None:
    data = InvoiceExtractionData(
        line_items=[
            InvoiceLineItem(description_of_goods="Paper", quantity=1),
            InvoiceLineItem(description_of_goods="Ink", quantity=1),
        ]
    )
    boxes = [
        _box("Paper", 0.1, 0.2),
        _box("1", 0.7, 0.2),
        _box("Ink", 0.1, 0.4),
        _box("1", 0.7, 0.4),
    ]

    first = _source(data, "line_items[0].quantity", boxes)
    second = _source(data, "line_items[1].quantity", boxes)

    assert first.status == "located" and first.boxes[0][1] == 0.2
    assert second.status == "located" and second.boxes[0][1] == 0.4


def test_unavailable_reasons_cover_not_found_low_quality_and_ocr_failure() -> None:
    invoice = InvoiceExtractionData(invoice_number="INV-1001")
    not_found = _source(invoice, "invoice_number", [])
    low_quality = _source(
        invoice,
        "invoice_number",
        [_box("INV-1999", 0.1, 0.1)],
        evidence_match_threshold=0.95,
    )
    ocr_failed = _source(invoice, "invoice_number", [], ocr_failed=True)

    assert not_found.reason == "not_found"
    assert low_quality.reason == "low_quality"
    assert ocr_failed.reason == "ocr_failed"
