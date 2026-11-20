"""Upload validation tests for the extraction endpoint."""

import binascii
import io
import logging
import struct
import zlib
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from docextract.api.routes import extract as extract_route
from docextract.core.config import Settings
from docextract.core.logging_config import JsonLogFormatter
from docextract.main import app
from docextract.schemas import InvoiceExtractionData, InvoiceLineItem
from docextract.services import extractor

_LIMIT = 1024


def _pdf() -> bytes:
    return _pdf_with_pages(1)


def _pdf_with_pages(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _jpeg(width: int = 1, height: int = 1) -> bytes:
    start_of_frame = (
        b"\xff\xc0\x00\x11\x08"
        + struct.pack(">HH", height, width)
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )
    return b"\xff\xd8" + start_of_frame + b"\xff\xd9"


def _png(width: int = 1, height: int = 1) -> bytes:
    header = b"\x89PNG\r\n\x1a\n"

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        header
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
        + chunk(b"IEND", b"")
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Use a small upload limit so boundary cases stay inexpensive."""
    monkeypatch.setattr(
        extract_route,
        "get_settings",
        lambda: Settings(
            max_upload_size_bytes=_LIMIT,
            max_pdf_pages=2,
            max_image_width=20,
            max_image_height=20,
        ),
    )
    return TestClient(app)


def _mock_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[bytes, str, str]]:
    calls: list[tuple[bytes, str, str]] = []

    async def extract(data: bytes, mime_type: str, filename: str) -> InvoiceExtractionData:
        calls.append((data, mime_type, filename))
        return InvoiceExtractionData(invoice_number="INV-1")

    monkeypatch.setattr(extract_route, "extract_document_data", extract)
    return calls


def _assert_error_response(
    response,
    code: str,
    message: str,
) -> None:
    request_id = response.headers["X-Request-ID"]
    assert response.json() == {
        "error": {"code": code, "message": message, "request_id": request_id}
    }


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("invoice.pdf", "application/pdf", _pdf()),
        ("invoice.jpg", "image/jpeg", _jpeg()),
        ("invoice.png", "image/png", _png()),
    ],
)
def test_valid_supported_file_reaches_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post(
        "/api/extract",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 200
    assert response.json()["invoice_number"] == "INV-1"
    assert calls == [(content, content_type, filename)]


def test_extraction_response_serializes_nullable_schema_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def extract(*args: object) -> InvoiceExtractionData:
        return InvoiceExtractionData(
            invoice_number="INV-SERIALIZE",
            line_items=[InvoiceLineItem(sr_no=1)],
        )

    monkeypatch.setattr(extract_route, "extract_document_data", extract)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == set(InvoiceExtractionData.model_fields)
    assert payload["invoice_number"] == "INV-SERIALIZE"
    assert payload["buyer_name"] is None
    assert set(payload["line_items"][0]) == set(InvoiceLineItem.model_fields)


def test_empty_upload_returns_bad_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"
    assert calls == []


def test_file_exactly_at_limit_reaches_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)
    pdf = _pdf()
    content = pdf.rsplit(b"%%EOF", maxsplit=1)[0] + b" " * (_LIMIT - len(pdf)) + b"%%EOF\n"

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    assert calls[0][0] == content


def test_file_over_limit_returns_payload_too_large(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", b"x" * (_LIMIT + 1), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert calls == []


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("invoice.pdf", "application/pdf", b"not a PDF"),
        ("invoice.pdf", "application/pdf", b"%PDF-1.7\nno end marker"),
        ("invoice.png", "image/png", b"\x89PNG\r\n\x1a\ntruncated"),
        ("invoice.jpg", "image/jpeg", b"\xff\xd8truncated"),
    ],
)
def test_invalid_document_content_returns_bad_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post("/api/extract", files={"file": (filename, content, content_type)})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DOCUMENT"
    assert calls == []


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("invoice.pdf", "image/png", _pdf()),
        ("invoice.png", "application/pdf", _png()),
        ("invoice.txt", "application/pdf", _pdf()),
    ],
)
def test_declared_type_mismatch_returns_unsupported_media_type(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post("/api/extract", files={"file": (filename, content, content_type)})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"
    assert calls == []


def test_unsupported_image_format_returns_unsupported_media_type(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.gif", b"GIF89a" + b"x" * 16, "image/gif")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"
    assert calls == []


@pytest.mark.parametrize("page_count", [1, 2])
def test_pdf_at_or_below_page_limit_reaches_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    page_count: int,
) -> None:
    calls = _mock_extraction(monkeypatch)
    content = _pdf_with_pages(page_count)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", content, "application/pdf")},
    )

    assert response.status_code == 200
    assert calls[0][0] == content


def test_pdf_above_page_limit_returns_payload_too_large(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf_with_pages(3), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PDF_PAGE_LIMIT_EXCEEDED"
    assert calls == []


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("invoice.png", "image/png", _png(20, 20)),
        ("invoice.jpg", "image/jpeg", _jpeg(20, 20)),
    ],
)
def test_image_at_dimension_limits_reaches_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post("/api/extract", files={"file": (filename, content, content_type)})

    assert response.status_code == 200
    assert calls[0][0] == content


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("invoice.png", "image/png", _png(21, 20)),
        ("invoice.png", "image/png", _png(20, 21)),
        ("invoice.jpg", "image/jpeg", _jpeg(21, 20)),
        ("invoice.jpg", "image/jpeg", _jpeg(20, 21)),
    ],
)
def test_image_over_dimension_limit_returns_payload_too_large(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    calls = _mock_extraction(monkeypatch)

    response = client.post("/api/extract", files={"file": (filename, content, content_type)})

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_DIMENSION_LIMIT_EXCEEDED"
    assert calls == []


def test_malformed_pdf_returns_bad_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)
    malformed_pdf = b"%PDF-1.4\nnot a valid PDF structure\n%%EOF\n"

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", malformed_pdf, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DOCUMENT"
    assert calls == []


def test_default_upload_limit_is_10_mib() -> None:
    assert Settings().max_upload_size_bytes == 10 * 1024 * 1024


def test_resource_limit_defaults() -> None:
    settings = Settings()

    assert settings.max_pdf_pages == 50
    assert settings.max_image_width == 10_000
    assert settings.max_image_height == 10_000


def test_provider_not_configured_returns_service_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key=None, gemini_api_key=None, _env_file=None),
    )

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 503
    _assert_error_response(
        response,
        "MISSING_PROVIDER_CONFIGURATION",
        "No AI extraction provider is configured.",
    )


def test_provider_failures_return_bad_gateway(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key="test-openai", gemini_api_key="test-gemini"),
    )

    def fail_openai(*args: object, **kwargs: object) -> InvoiceExtractionData:
        raise RuntimeError("OpenAI unavailable")

    def fail_gemini(*args: object, **kwargs: object) -> InvoiceExtractionData:
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(extractor, "_extract_with_openai", fail_openai)
    monkeypatch.setattr(extractor, "_extract_with_gemini", fail_gemini)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 502
    _assert_error_response(
        response,
        "PROVIDER_FAILURE",
        "Invoice extraction failed with configured AI providers.",
    )


def test_invalid_provider_response_returns_bad_gateway(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key="test-openai", gemini_api_key="test-gemini"),
    )

    def invalid_openai(*args: object, **kwargs: object) -> InvoiceExtractionData:
        raise ValueError("Provider response could not be parsed")

    class FakeGeminiModels:
        def generate_content(self, **kwargs: object) -> object:
            return type("Response", (), {"text": '{"invoice_number": 123}'})()

    class FakeGeminiClient:
        def __init__(self, **kwargs: object) -> None:
            self.models = FakeGeminiModels()

    monkeypatch.setattr(extractor, "_extract_with_openai", invalid_openai)
    monkeypatch.setattr(extractor.genai, "Client", FakeGeminiClient)

    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 502
    _assert_error_response(
        response,
        "INVALID_AI_RESPONSE",
        "AI provider returned an invalid response.",
    )


@pytest.mark.parametrize(
    ("category", "status_code", "code"),
    [
        ("authentication", 502, "PROVIDER_AUTHENTICATION_FAILURE"),
        ("rate-limit", 503, "PROVIDER_RATE_LIMIT"),
        ("timeout", 504, "PROVIDER_TIMEOUT"),
        ("provider-error", 502, "PROVIDER_FAILURE"),
        ("invalid-response", 502, "INVALID_AI_RESPONSE"),
    ],
)
def test_provider_error_categories_use_standard_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    status_code: int,
    code: str,
) -> None:
    async def fail(*args: object) -> InvoiceExtractionData:
        raise extractor.ExtractionProviderError("private provider details", category)

    monkeypatch.setattr(extract_route, "extract_document_data", fail)
    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert "private provider details" not in response.text


def test_missing_file_returns_standard_validation_error(client: TestClient) -> None:
    response = client.post("/api/extract")

    assert response.status_code == 422
    _assert_error_response(response, "INVALID_REQUEST", "The request is invalid.")


def test_unknown_route_uses_standard_http_error(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    _assert_error_response(response, "NOT_FOUND", "The requested resource was not found.")


def test_unexpected_error_returns_generic_internal_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(*args: object) -> InvoiceExtractionData:
        raise RuntimeError("secret or document content")

    monkeypatch.setattr(extract_route, "extract_document_data", fail)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    assert response.status_code == 500
    _assert_error_response(
        response,
        "INTERNAL_SERVER_ERROR",
        "An unexpected server error occurred.",
    )
    assert "secret or document content" not in response.text


def test_request_id_is_generated_returned_and_unique(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_extraction(monkeypatch)
    first = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )
    second = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]
    first_file_id = first.headers["X-File-ID"]
    second_file_id = second.headers["X-File-ID"]
    UUID(first_id)
    UUID(second_id)
    UUID(first_file_id)
    UUID(second_file_id)
    assert first.headers["X-Trace-ID"] == first_id
    assert second.headers["X-Trace-ID"] == second_id
    assert first_id != second_id
    assert first_file_id != second_file_id
    assert "request_id" not in first.json()


def test_provider_logs_carry_request_id_and_do_not_log_sensitive_values(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    api_key = "secret-api-key-marker"
    invoice_value = "private-invoice-value-marker"
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key=api_key, gemini_api_key=None),
    )

    def succeed(*args: object) -> InvoiceExtractionData:
        return InvoiceExtractionData(buyer_name=invoice_value)

    monkeypatch.setattr(extractor, "_extract_with_openai", succeed)
    caplog.set_level(logging.INFO)
    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    request_id = response.headers["X-Request-ID"]
    provider_events = [
        record
        for record in caplog.records
        if getattr(record, "event", "").startswith("provider_attempt_")
    ]
    assert [record.event for record in provider_events] == [
        "provider_attempt_started",
        "provider_attempt_finished",
    ]
    assert all(record.request_id == request_id for record in provider_events)
    assert provider_events[-1].provider == "OpenAI"
    assert provider_events[-1].model == "gpt-6-luna"
    assert provider_events[-1].outcome == "success"
    log_output = "\n".join(JsonLogFormatter().format(record) for record in caplog.records)
    assert api_key not in log_output
    assert invoice_value not in log_output
    assert invoice_value in response.text


def test_provider_failure_logs_safe_stack_and_request_outcome(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_detail = "private-provider-error-marker"
    monkeypatch.setattr(
        extractor,
        "get_settings",
        lambda: Settings(openai_api_key="test-key", gemini_api_key=None),
    )

    def fail(*args: object) -> InvoiceExtractionData:
        raise RuntimeError(private_detail)

    monkeypatch.setattr(extractor, "_extract_with_openai", fail)
    caplog.set_level(logging.INFO)
    response = client.post(
        "/api/extract",
        files={"file": ("invoice.pdf", _pdf(), "application/pdf")},
    )

    request_id = response.headers["X-Request-ID"]
    failure = next(
        record
        for record in caplog.records
        if getattr(record, "event", "") == "provider_attempt_failed"
    )
    outcome = next(
        record
        for record in caplog.records
        if getattr(record, "event", "") == "request_finished"
    )
    assert failure.request_id == request_id
    assert failure.error_type == "RuntimeError"
    assert failure.stack_trace
    assert outcome.request_id == request_id
    assert outcome.http_status == 502
    assert outcome.outcome == "failure"
    log_output = "\n".join(JsonLogFormatter().format(record) for record in caplog.records)
    assert private_detail not in log_output
