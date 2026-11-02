"""Upload validation tests for the extraction endpoint."""

import binascii
import io
import struct
import zlib

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from docextract.api.routes import extract as extract_route
from docextract.core.config import Settings
from docextract.main import app
from docextract.schemas import InvoiceExtractionData

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
    assert calls == []


def test_default_upload_limit_is_10_mib() -> None:
    assert Settings().max_upload_size_bytes == 10 * 1024 * 1024


def test_resource_limit_defaults() -> None:
    settings = Settings()

    assert settings.max_pdf_pages == 50
    assert settings.max_image_width == 10_000
    assert settings.max_image_height == 10_000
