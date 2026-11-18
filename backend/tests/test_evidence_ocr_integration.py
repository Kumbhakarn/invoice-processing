"""Small real-model smoke test for the default CPU OCR package."""

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from docextract.services.evidence.ocr import RapidOcrEngine


@pytest.mark.slow
def test_rapidocr_runs_with_models_bundled_in_installed_package() -> None:
    image = Image.new("RGB", (600, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "INV-42", fill="black", font=ImageFont.load_default())
    image = image.resize((1200, 360))
    output = io.BytesIO()
    image.save(output, format="PNG")

    boxes = RapidOcrEngine().extract(output.getvalue(), page_number=1)

    assert boxes
    assert all(box.page == 1 and box.source == "ocr" for box in boxes)
    assert all(0 <= value <= 1 for box in boxes for value in box.bbox)
