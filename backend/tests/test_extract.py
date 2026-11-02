"""Upload validation tests for the extraction endpoint."""

import pytest
from fastapi.testclient import TestClient

from docextract.api.routes import extract as extract_route
from docextract.core.config import Settings
from docextract.main import app
from docextract.schemas import InvoiceExtractionData

_LIMIT = 8


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Use a small upload limit so boundary cases stay inexpensive."""
    monkeypatch.setattr(
        extract_route,
        "get_settings",
        lambda: Settings(max_upload_size_bytes=_LIMIT),
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


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("invoice.pdf", "application/pdf"), ("invoice.png", "image/png")],
)
def test_valid_pdf_and_image_reach_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
) -> None:
    calls = _mock_extraction(monkeypatch)
    content = b"document"

    response = client.post(
        "/api/extract",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 200
    assert response.json()["invoice_number"] == "INV-1"
    assert calls == [(content, content_type, filename)]


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
    assert calls == []


def test_file_exactly_at_limit_reaches_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_extraction(monkeypatch)
    content = b"x" * _LIMIT

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
    assert calls == []


def test_default_upload_limit_is_10_mib() -> None:
    assert Settings().max_upload_size_bytes == 10 * 1024 * 1024
