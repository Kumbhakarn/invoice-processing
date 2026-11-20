"""Interim evidence endpoint routing and safe error mapping tests."""

from uuid import UUID

from fastapi.testclient import TestClient

from docextract.api.routes import evidence as evidence_route
from docextract.core.config import Settings
from docextract.main import app
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import EvidenceExtractionResponse
from docextract.services.evidence.ocr import OcrTimeoutError


def _response() -> EvidenceExtractionResponse:
    return EvidenceExtractionResponse(
        data=InvoiceExtractionData(),
        fields={},
        pages=[{"page": 1, "width": 10, "height": 10}],
        meta={"timings_ms": {}, "provider_usage": []},
    )


def test_evidence_endpoint_accepts_tiff_and_returns_page_metadata(monkeypatch) -> None:
    monkeypatch.setattr(evidence_route, "get_settings", lambda: Settings())

    async def fake_extract(*args, **kwargs):
        return _response()

    monkeypatch.setattr(evidence_route, "extract_evidence_document", fake_extract)
    response = TestClient(app).post(
        "/api/extract/evidence",
        files={"file": ("invoice.tif", b"II*\x00fixture", "image/tiff")},
    )

    assert response.status_code == 200
    assert response.json()["pages"] == [{"page": 1, "width": 10, "height": 10}]
    assert response.headers["x-request-id"]
    UUID(response.headers["x-trace-id"])
    UUID(response.headers["x-file-id"])
    assert response.headers["x-trace-id"] == response.headers["x-request-id"]


def test_reuploading_same_evidence_file_gets_new_file_id(monkeypatch) -> None:
    monkeypatch.setattr(evidence_route, "get_settings", lambda: Settings())

    async def fake_extract(*args, **kwargs):
        return _response()

    monkeypatch.setattr(evidence_route, "extract_evidence_document", fake_extract)
    client = TestClient(app)
    upload = {"file": ("invoice.tif", b"II*\x00fixture", "image/tiff")}
    first = client.post("/api/extract/evidence", files=upload)
    second = client.post("/api/extract/evidence", files=upload)

    assert first.headers["x-file-id"] != second.headers["x-file-id"]
    assert first.headers["x-trace-id"] != second.headers["x-trace-id"]


def test_evidence_endpoint_maps_ocr_timeout_to_stable_error(monkeypatch) -> None:
    monkeypatch.setattr(evidence_route, "get_settings", lambda: Settings())

    async def timeout(*args, **kwargs):
        raise OcrTimeoutError("private engine detail")

    monkeypatch.setattr(evidence_route, "extract_evidence_document", timeout)
    response = TestClient(app).post(
        "/api/extract/evidence",
        files={"file": ("invoice.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "OCR_TIMEOUT"
    assert "private engine detail" not in response.text
