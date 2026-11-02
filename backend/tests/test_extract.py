"""Upload validation tests for the extraction endpoint."""

import binascii
import struct
import zlib

import pytest
from fastapi.testclient import TestClient

from docextract.api.routes import extract as extract_route
from docextract.core.config import Settings
from docextract.main import app
from docextract.schemas import InvoiceExtractionData

_LIMIT = 128


def _pdf() -> bytes:
    return b"%PDF-1.4\nInvoice\n%%EOF\n"


def _jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x04JFIF\xff\xd9"


def _png() -> bytes:
    header = b"\x89PNG\r\n\x1a\n"

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
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
    content = b"%PDF-1.4\n" + b"x" * (_LIMIT - len(b"%PDF-1.4\n%%EOF\n")) + b"%%EOF\n"

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
    assert calls == []


def test_default_upload_limit_is_10_mib() -> None:
    assert Settings().max_upload_size_bytes == 10 * 1024 * 1024
