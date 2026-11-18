"""Page decoding tests use generated, deterministic invoice-like documents."""

import io

import pytest
from PIL import Image

from docextract.core.config import Settings
from docextract.services.evidence.pages import (
    DocumentDecodeError,
    decode_document,
    page_metadata,
)


def _pdf_page_fixture(second_page_text: str | None = "Second page invoice text") -> bytes:
    """Build two 612x792 pages with known top-left text placement."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        _stream(b"BT /F1 12 Tf 72 720 Td (Invoice number: INV-42) Tj ET"),
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
        _stream(
            f"BT /F1 12 Tf 72 720 Td ({second_page_text}) Tj ET".encode("ascii")
            if second_page_text
            else b""
        ),
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode())
        result.extend(body + b"\nendobj\n")
    xref_offset = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n".encode())
    result.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010} 00000 n \n".encode())
    result.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return bytes(result)


def _stream(content: bytes) -> bytes:
    return b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"


def _image_bytes(image_format: str, *, frames: int = 1, size: tuple[int, int] = (20, 10)) -> bytes:
    image = Image.new("RGB", size, "white")
    buffer = io.BytesIO()
    if image_format == "TIFF" and frames > 1:
        image.save(
            buffer,
            format=image_format,
            save_all=True,
            append_images=[image.copy() for _ in range(frames - 1)],
        )
    else:
        image.save(buffer, format=image_format)
    return buffer.getvalue()


def test_digital_two_page_pdf_has_one_based_words_and_normalized_boxes() -> None:
    result = decode_document(_pdf_page_fixture(), "application/pdf", Settings())

    assert [page.page for page in result.pages] == [1, 2]
    assert all(not page.requires_ocr and page.raster_png is None for page in result.pages)
    assert [(page.page, page.width, page.height) for page in page_metadata(result)] == [
        (1, 1700, 2200),
        (2, 1700, 2200),
    ]
    invoice_word = next(box for box in result.pages[0].text_boxes if box.text == "Invoice")
    assert invoice_word.page == 1
    assert invoice_word.source == "text_layer"
    assert 0.1 < invoice_word.bbox[0] < 0.13
    assert 0.05 < invoice_word.bbox[1] < 0.12
    assert all(0 <= value <= 1 for value in invoice_word.bbox)


def test_mixed_pdf_keeps_digital_text_and_renders_scanned_page() -> None:
    result = decode_document(
        _pdf_page_fixture(second_page_text=None),
        "application/pdf",
        Settings(evidence_render_dpi=72),
    )

    first, second = result.pages
    assert first.page == 1 and not first.requires_ocr
    assert second.page == 2 and second.requires_ocr
    assert second.text_boxes == ()
    assert second.raster_png is not None
    with Image.open(io.BytesIO(second.raster_png)) as rendered:
        assert rendered.size == (612, 792)


@pytest.mark.parametrize(
    ("image_format", "mime_type"),
    [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("TIFF", "image/tiff")],
)
def test_raster_images_are_ocr_ready(image_format: str, mime_type: str) -> None:
    result = decode_document(_image_bytes(image_format), mime_type, Settings())

    page = result.pages[0]
    assert (page.page, page.width, page.height) == (1, 20, 10)
    assert page.requires_ocr
    assert page.text_boxes == ()
    assert page.raster_png is not None


def test_multipage_tiff_uses_deterministic_one_based_order() -> None:
    result = decode_document(_image_bytes("TIFF", frames=2), "image/tiff", Settings())

    assert [page.page for page in result.pages] == [1, 2]


def test_page_limit_and_image_dimension_limit_are_enforced() -> None:
    with pytest.raises(DocumentDecodeError, match="page count"):
        decode_document(_image_bytes("TIFF", frames=2), "image/tiff", Settings(max_pdf_pages=1))
    with pytest.raises(DocumentDecodeError, match="dimensions"):
        decode_document(
            _image_bytes("PNG", size=(21, 10)),
            "image/png",
            Settings(max_image_width=20, max_image_height=20),
        )


def test_pdf_page_limit_is_enforced() -> None:
    with pytest.raises(DocumentDecodeError, match="page count"):
        decode_document(_pdf_page_fixture(), "application/pdf", Settings(max_pdf_pages=1))
