"""OCR adapter and asynchronous worker behavior using fake engine runtimes."""

import asyncio
import io
import tempfile
import threading
import time
from typing import Any

import pytest
from PIL import Image

from docextract.core.config import Settings
from docextract.services.evidence.ocr import (
    OcrEngineUnavailableError,
    OcrPageProcessor,
    OcrTimeoutError,
    PaddleOcrEngine,
    RapidOcrEngine,
    ocr_engine_factory,
)
from docextract.services.evidence.types import DecodedPage, TextBox


def _png() -> bytes:
    image = Image.new("RGB", (100, 50), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _page(number: int, *, requires_ocr: bool = True) -> DecodedPage:
    return DecodedPage(
        page=number,
        width=100,
        height=50,
        text_boxes=(),
        requires_ocr=requires_ocr,
        raster_png=_png() if requires_ocr else None,
    )


class _RapidRuntime:
    def __call__(self, _image: Any) -> tuple[list[Any], list[float]]:
        rows = [([[10, 5], [50, 5], [50, 15], [10, 15]], "INVOICE", 0.91)]
        return rows, [0.1, 0.2, 0.3]


class _PaddleRuntime:
    def predict(self, _image: Any) -> list[dict[str, Any]]:
        return [
            {
                "rec_texts": ["INV-1", "2026-01-02"],
                "rec_scores": [0.8, 0.95],
                "rec_boxes": [[10, 5, 40, 15], [20, 20, 80, 30]],
            }
        ]


def test_rapidocr_adapter_maps_polygon_text_and_confidence() -> None:
    result = RapidOcrEngine(runtime=_RapidRuntime()).extract(_png(), page_number=3)

    assert result == [
        TextBox(
            page=3,
            text="INVOICE",
            bbox=(0.1, 0.1, 0.5, 0.3),
            source="ocr",
            ocr_confidence=0.91,
        )
    ]


def test_paddleocr_adapter_maps_xyxy_boxes() -> None:
    result = PaddleOcrEngine(runtime=_PaddleRuntime()).extract(_png(), page_number=2)

    assert [box.text for box in result] == ["INV-1", "2026-01-02"]
    assert result[0].page == 2
    assert result[0].bbox == (0.1, 0.1, 0.4, 0.3)
    assert result[0].ocr_confidence == 0.8
    assert all(box.source == "ocr" for box in result)


def test_engine_selection_is_lazy_and_configurable() -> None:
    assert ocr_engine_factory(Settings(evidence_ocr_engine="rapidocr")) is RapidOcrEngine
    with tempfile.TemporaryDirectory() as temporary_dir:
        factory = ocr_engine_factory(
            Settings(evidence_ocr_engine="paddleocr", evidence_ocr_model_dir=temporary_dir)
        )
    assert getattr(factory, "func", None) is PaddleOcrEngine


def test_missing_optional_engine_has_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    original_import = builtins.__import__

    def import_without_paddle(name: str, *args: object, **kwargs: object) -> Any:
        if name == "paddleocr":
            raise ImportError("missing mocked package")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_paddle)

    with tempfile.TemporaryDirectory() as temporary_dir:
        from pathlib import Path

        model_dir = Path(temporary_dir)
        (model_dir / "det").mkdir()
        (model_dir / "rec").mkdir()
        with pytest.raises(OcrEngineUnavailableError, match="ocr-paddle") as caught:
            PaddleOcrEngine(model_dir=model_dir)
    assert caught.value.code == "OCR_ENGINE_UNAVAILABLE"


def test_ocr_runs_in_parallel_and_returns_boxes_in_page_order() -> None:
    thread_ids: set[int] = set()
    both_started = threading.Barrier(2)

    class FakeEngine:
        def extract(self, _image: bytes, page_number: int) -> list[TextBox]:
            thread_ids.add(threading.get_ident())
            both_started.wait(timeout=2)
            time.sleep(0.01 * (3 - page_number))
            return [
                TextBox(
                    page=page_number,
                    text=f"page-{page_number}",
                    bbox=(0.1, 0.1, 0.2, 0.2),
                    source="ocr",
                    ocr_confidence=0.9,
                )
            ]

    processor = OcrPageProcessor(FakeEngine, workers=2, timeout_seconds=3)
    try:
        result = asyncio.run(processor.extract_pages([_page(1), _page(2)]))
    finally:
        processor.close()

    assert [box.page for box in result] == [1, 2]
    assert len(thread_ids) == 2
    assert threading.get_ident() not in thread_ids


def test_text_layer_pages_skip_ocr() -> None:
    def fail_if_created() -> RapidOcrEngine:
        raise AssertionError("OCR engine should not be initialized")

    processor = OcrPageProcessor(fail_if_created, workers=1, timeout_seconds=1)
    try:
        result = asyncio.run(processor.extract_pages([_page(1, requires_ocr=False)]))
    finally:
        processor.close()

    assert result == []


def test_ocr_timeout_raises_coded_error() -> None:
    class SlowEngine:
        def extract(self, _image: bytes, _page_number: int) -> list[TextBox]:
            time.sleep(0.1)
            return []

    processor = OcrPageProcessor(SlowEngine, workers=1, timeout_seconds=0.01)
    try:
        with pytest.raises(OcrTimeoutError, match="time limit") as caught:
            asyncio.run(processor.extract_pages([_page(1)]))
        assert caught.value.code == "OCR_TIMEOUT"
    finally:
        processor.close()
