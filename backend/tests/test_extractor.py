"""Extraction service tests using mocked provider functions only."""

import asyncio

import pytest

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.services import extractor


def test_openai_failure_falls_back_to_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key="test-openai", gemini_api_key="test-gemini"),
    )
    calls: list[str] = []

    def fail_openai(*args: object) -> InvoiceExtractionData:
        calls.append("openai")
        raise RuntimeError("offline")

    def succeed_gemini(*args: object) -> InvoiceExtractionData:
        calls.append("gemini")
        return InvoiceExtractionData(invoice_number="INV-FALLBACK")

    monkeypatch.setattr(extractor, "_extract_with_openai", fail_openai)
    monkeypatch.setattr(extractor, "_extract_with_gemini", succeed_gemini)

    result = asyncio.run(
        extractor.extract_document_data(b"document", "application/pdf", "invoice.pdf")
    )

    assert result.invoice_number == "INV-FALLBACK"
    assert calls == ["openai", "gemini"]
