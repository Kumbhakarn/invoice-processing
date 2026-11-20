"""Evidence orchestration tests with document and OCR providers mocked."""

import asyncio

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import FieldConfidenceAssessment, RawFieldText
from docextract.services.evidence import pipeline
from docextract.services.evidence.types import DecodedDocument, DecodedPage, TextBox
from docextract.services.extractor import ExtractionResult


def test_pipeline_maps_pages_and_grounds_raw_text(monkeypatch) -> None:
    data = InvoiceExtractionData(invoice_number="INV-42", invoice_date="2025-01-15")
    boxes = (
        TextBox(1, "Invoice No: INV-42", (0.1, 0.1, 0.5, 0.13)),
        TextBox(1, "Date: 15/01/2025", (0.1, 0.2, 0.4, 0.23)),
    )
    document = DecodedDocument((DecodedPage(1, 100, 200, boxes, False, None),))

    def decode(*args):
        return document

    async def extract(*args, **kwargs):
        return ExtractionResult(
            data,
            (),
            (RawFieldText(field="invoice_date", raw="15/01/2025"),),
            (FieldConfidenceAssessment(field="invoice_number", confidence="High"),),
        )

    monkeypatch.setattr(pipeline, "decode_document", decode)
    monkeypatch.setattr(pipeline, "extract_document_with_usage", extract)

    result = asyncio.run(
        pipeline.extract_evidence_document(
            b"%PDF-1.4\n%%EOF", "application/pdf", "invoice.pdf", Settings()
        )
    )

    assert result.pages[0].page == 1
    assert result.fields["invoice_date"].raw == "15/01/2025"
    assert result.fields["invoice_number"].value == "INV-42"
    assert result.fields["invoice_number"].confidence == "High"
    assert result.fields["invoice_date"].confidence is None
    assert set(result.meta.timings_ms) == {
        "validation",
        "text_layer",
        "ocr",
        "llm",
        "matching",
        "total",
    }


def test_pipeline_uses_mock_ocr_for_scanned_page(monkeypatch) -> None:
    from contextlib import AbstractContextManager

    ocr_box = TextBox(1, "INV-8", (0.1, 0.1, 0.2, 0.12), source="ocr", ocr_confidence=0.91)
    page = DecodedPage(1, 100, 200, (), True, b"png")

    class FakeProcessor(AbstractContextManager):
        def __init__(self, *args, **kwargs):
            pass

        async def extract_pages(self, pages):
            return [ocr_box]

        def __exit__(self, *args):
            return None

    async def extract(*args, **kwargs):
        return ExtractionResult(InvoiceExtractionData(invoice_number="INV-8"), ())

    monkeypatch.setattr(
        pipeline,
        "decode_document",
        lambda *args: DecodedDocument((page,)),
    )
    monkeypatch.setattr(pipeline, "ocr_engine_factory", lambda settings: object())
    monkeypatch.setattr(pipeline, "OcrPageProcessor", FakeProcessor)
    monkeypatch.setattr(pipeline, "extract_document_with_usage", extract)

    result = asyncio.run(
        pipeline.extract_evidence_document(
            b"%PDF-1.4\n%%EOF", "application/pdf", "scan.pdf", Settings()
        )
    )

    assert result.fields["invoice_number"].source.page == 1
    assert result.fields["invoice_number"].source.evidence_text == "INV-8"
