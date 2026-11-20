"""Extraction service tests using mocked provider functions only."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from docextract.core.config import Settings
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import EvidenceProviderResponse, FieldConfidenceAssessment
from docextract.services import extractor
from docextract.services.usage import ProviderUsage, calculate_cost, reported_usage


def _settings(monkeypatch: pytest.MonkeyPatch, openai: str | None, gemini: str | None) -> None:
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key=openai, gemini_api_key=gemini),
    )


def _run() -> InvoiceExtractionData:
    return asyncio.run(
        extractor.extract_document_data(b"document", "application/pdf", "invoice.pdf")
    )


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


def test_openai_success_does_not_call_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")
    calls: list[str] = []
    monkeypatch.setattr(
        extractor,
        "_extract_with_openai",
        lambda *args: (calls.append("openai") or InvoiceExtractionData(invoice_number="INV-1")),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_with_gemini",
        lambda *args: (calls.append("gemini") or InvoiceExtractionData()),
    )

    result = _run()

    assert isinstance(result, InvoiceExtractionData)
    assert result.invoice_number == "INV-1"
    assert calls == ["openai"]


@pytest.mark.parametrize(
    ("openai_key", "gemini_key", "expected_calls"),
    [
        (None, "gemini-key", ["gemini"]),
        ("openai-key", None, ["openai"]),
        (None, None, []),
    ],
)
def test_missing_credentials_only_attempt_configured_providers(
    monkeypatch: pytest.MonkeyPatch,
    openai_key: str | None,
    gemini_key: str | None,
    expected_calls: list[str],
) -> None:
    _settings(monkeypatch, openai_key, gemini_key)
    calls: list[str] = []
    monkeypatch.setattr(
        extractor,
        "_extract_with_openai",
        lambda *args: (calls.append("openai") or InvoiceExtractionData()),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_with_gemini",
        lambda *args: (calls.append("gemini") or InvoiceExtractionData()),
    )

    if not expected_calls:
        with pytest.raises(extractor.ExtractionNotConfiguredError):
            _run()
    else:
        _run()
    assert calls == expected_calls


def test_openai_timeout_falls_back_once_to_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")
    calls: list[str] = []

    def timeout(*args: object) -> InvoiceExtractionData:
        calls.append("openai")
        raise TimeoutError("timed out")

    monkeypatch.setattr(extractor, "_extract_with_openai", timeout)
    monkeypatch.setattr(
        extractor,
        "_extract_with_gemini",
        lambda *args: (calls.append("gemini") or InvoiceExtractionData(invoice_number="fallback")),
    )

    assert _run().invoice_number == "fallback"
    assert calls == ["openai", "gemini"]


def test_gemini_timeout_is_reported_after_openai_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")
    calls: list[str] = []

    def fail_openai(*args: object) -> InvoiceExtractionData:
        calls.append("openai")
        raise RuntimeError("offline")

    def timeout_gemini(*args: object) -> InvoiceExtractionData:
        calls.append("gemini")
        raise TimeoutError("timed out")

    monkeypatch.setattr(extractor, "_extract_with_openai", fail_openai)
    monkeypatch.setattr(extractor, "_extract_with_gemini", timeout_gemini)
    with pytest.raises(extractor.ExtractionProviderError, match="TimeoutError"):
        _run()
    assert calls == ["openai", "gemini"]


def test_both_providers_fail_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")
    calls: list[str] = []

    def fail(name: str):
        def provider(*args: object) -> InvoiceExtractionData:
            calls.append(name)
            raise RuntimeError("unavailable")

        return provider

    monkeypatch.setattr(extractor, "_extract_with_openai", fail("openai"))
    monkeypatch.setattr(extractor, "_extract_with_gemini", fail("gemini"))
    with pytest.raises(extractor.ExtractionProviderError):
        _run()
    assert calls == ["openai", "gemini"]


@pytest.mark.parametrize(
    "error",
    [ValueError("bad JSON"), TypeError("invalid field"), RuntimeError("empty response")],
)
def test_invalid_or_empty_openai_output_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")
    calls: list[str] = []

    def invalid(*args: object) -> InvoiceExtractionData:
        calls.append("openai")
        raise error

    monkeypatch.setattr(extractor, "_extract_with_openai", invalid)
    monkeypatch.setattr(
        extractor,
        "_extract_with_gemini",
        lambda *args: (calls.append("gemini") or InvoiceExtractionData(invoice_number="ok")),
    )
    assert _run().invoice_number == "ok"
    assert calls == ["openai", "gemini"]


def test_openai_adapter_uses_structured_sdk_response_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    expected = InvoiceExtractionData(invoice_number="SDK-1")

    class Responses:
        def parse(self, **kwargs: object) -> object:
            received["parse"] = kwargs
            return SimpleNamespace(
                output_parsed=expected,
                usage=SimpleNamespace(input_tokens=11, output_tokens=5, total_tokens=16),
            )

    class Client:
        def __init__(self, **kwargs: object) -> None:
            received["client"] = kwargs
            self.responses = Responses()

    monkeypatch.setattr(extractor, "OpenAI", Client)
    result = extractor._extract_with_openai(
        b"pdf", "application/pdf", "invoice.pdf", Settings(openai_api_key="key")
    )
    assert result.data is expected
    assert result.usage == ProviderUsage(11, 5, 16)
    assert received["client"] == {"api_key": "key", "timeout": 60.0}
    assert received["parse"]["text_format"] is InvoiceExtractionData  # type: ignore[index]


def test_openai_evidence_adapter_requests_qualitative_confidence_without_logprobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}
    parsed = EvidenceProviderResponse(
        data=InvoiceExtractionData(invoice_number="INV-1"),
        raw_fields=[],
        field_confidences=[FieldConfidenceAssessment(field="invoice_number", confidence="High")],
    )

    class Responses:
        def parse(self, **kwargs: object) -> object:
            received["parse"] = kwargs
            return SimpleNamespace(output_parsed=parsed, usage=None)

    class Client:
        def __init__(self, **kwargs: object) -> None:
            self.responses = Responses()

    monkeypatch.setattr(extractor, "OpenAI", Client)
    result = extractor._extract_evidence_with_openai(
        b"pdf", "application/pdf", "invoice.pdf", Settings(openai_api_key="key")
    )

    assert result.field_confidences == tuple(parsed.field_confidences)
    parse_kwargs = received["parse"]
    assert parse_kwargs["text_format"] is EvidenceProviderResponse  # type: ignore[index]
    assert "include" not in parse_kwargs  # type: ignore[operator]


@pytest.mark.parametrize("response_text", [None, "not json", '{"invoice_number": 123}'])
def test_gemini_adapter_rejects_empty_malformed_and_schema_invalid_data(
    monkeypatch: pytest.MonkeyPatch,
    response_text: str | None,
) -> None:
    received: dict[str, object] = {}

    class Models:
        def generate_content(self, **kwargs: object) -> object:
            received["generate"] = kwargs
            return SimpleNamespace(text=response_text)

    class Client:
        def __init__(self, **kwargs: object) -> None:
            received["client"] = kwargs
            self.models = Models()

    monkeypatch.setattr(extractor.genai, "Client", Client)
    with pytest.raises((ValueError, ValidationError)):
        extractor._extract_with_gemini(
            b"pdf", "application/pdf", Settings(gemini_api_key="key")
        )
    assert received["client"]["http_options"].timeout == 60_000  # type: ignore[index]
    assert received["generate"]["config"].response_schema is InvoiceExtractionData  # type: ignore[index]


def test_provider_usage_is_extracted_from_sdk_response_shapes() -> None:
    openai = reported_usage(
        SimpleNamespace(usage=SimpleNamespace(input_tokens=12, output_tokens=8, total_tokens=20)),
        "OpenAI",
    )
    gemini = reported_usage(
        SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=15, candidates_token_count=9, total_token_count=24
            )
        ),
        "Gemini",
    )
    missing = reported_usage(SimpleNamespace(usage_metadata=None), "Gemini")
    assert openai == ProviderUsage(12, 8, 20)
    assert gemini == ProviderUsage(15, 9, 24)
    assert missing.input_tokens is None and missing.output_tokens is None


def test_cost_uses_configured_model_and_version_and_unknown_is_not_guessed() -> None:
    pricing = '{"OpenAI":{"model-a":{"input_per_million_usd":2,"output_per_million_usd":4}}}'
    usage = ProviderUsage(1_000_000, 500_000, 1_500_000)
    cost = calculate_cost("OpenAI", "model-a", usage, pricing, "2026-01")
    unknown_model = calculate_cost("OpenAI", "model-b", usage, pricing, "2026-01")
    missing_usage = calculate_cost("OpenAI", "model-a", ProviderUsage(), pricing, "2026-01")
    assert cost.amount_usd == Decimal("4")
    assert cost.pricing_version == "2026-01"
    assert unknown_model.amount_usd is None
    assert missing_usage.amount_usd is None


def test_fallback_metadata_records_failed_primary_and_successful_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, "test-openai", "test-gemini")

    def fail(*args: object) -> extractor.ProviderCallResult:
        raise RuntimeError("offline")

    def succeed(*args: object) -> extractor.ProviderCallResult:
        return extractor.ProviderCallResult(
            InvoiceExtractionData(invoice_number="fallback"), ProviderUsage(7, 3, 10)
        )

    monkeypatch.setattr(extractor, "_extract_with_openai", fail)
    monkeypatch.setattr(extractor, "_extract_with_gemini", succeed)
    result = asyncio.run(
        extractor.extract_document_with_usage(b"document", "application/pdf", "invoice.pdf")
    )
    assert result.data.invoice_number == "fallback"
    assert [(attempt.outcome, attempt.fallback_used) for attempt in result.attempts] == [
        ("failure", False), ("success", True)
    ]
    assert result.attempts[0].usage.total_tokens is None
    assert result.attempts[1].usage.total_tokens == 10
