"""Pluggable CPU OCR engines and bounded asynchronous page processing."""

from __future__ import annotations

import asyncio
import io
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from PIL import Image

from docextract.core.config import Settings
from docextract.services.evidence.types import DecodedPage, TextBox


class OcrEngine(Protocol):
    """Synchronous engine interface; page number keeps evidence 1-based."""

    def extract(self, page_image: bytes, page_number: int) -> list[TextBox]:
        """Read actual text and normalized boxes from one raster page."""


class OcrError(RuntimeError):
    """Base class for OCR initialization and processing errors."""


class OcrEngineUnavailableError(OcrError):
    """Selected optional OCR engine is not installed or cannot initialize."""

    code = "OCR_ENGINE_UNAVAILABLE"


class OcrTimeoutError(OcrError):
    """OCR did not finish within its configured time limit."""

    code = "OCR_TIMEOUT"


class OcrProcessingError(OcrError):
    """OCR failed for a document page."""


EngineFactory = Callable[[], OcrEngine]


class RapidOcrEngine:
    """RapidOCR ONNX Runtime adapter; its package bundles CPU ONNX models."""

    def __init__(self, runtime: Any | None = None) -> None:
        if runtime is None:
            try:
                rapid_module = import_module("rapidocr_onnxruntime")
            except ImportError as exc:
                raise OcrEngineUnavailableError(
                    "RapidOCR is unavailable; install rapidocr-onnxruntime to use it."
                ) from exc
            try:
                runtime = rapid_module.RapidOCR()
            except Exception as exc:
                raise OcrEngineUnavailableError(
                    "RapidOCR could not initialize its local models."
                ) from exc
        self._runtime = runtime

    def extract(self, page_image: bytes, page_number: int) -> list[TextBox]:
        image, width, height = _read_image(page_image)
        try:
            numpy = import_module("numpy")
        except ImportError as exc:
            raise OcrEngineUnavailableError("RapidOCR requires NumPy.") from exc
        try:
            result = self._runtime(numpy.asarray(image))
        except Exception as exc:
            raise OcrProcessingError("RapidOCR failed to process a page.") from exc
        rows = result[0] if isinstance(result, tuple) else result
        if rows is None:
            return []
        boxes: list[TextBox] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 3:
                continue
            polygon, text, confidence = row[:3]
            boxes.append(
                _text_box(
                    polygon,
                    str(text),
                    float(confidence),
                    page_number,
                    width,
                    height,
                )
            )
        return boxes


class PaddleOcrEngine:
    """PaddleOCR 3 adapter, loaded only when selected in configuration."""

    def __init__(self, runtime: Any | None = None, *, model_dir: Path | None = None) -> None:
        if runtime is None:
            if (
                model_dir is None
                or not (model_dir / "det").is_dir()
                or not (model_dir / "rec").is_dir()
            ):
                raise OcrEngineUnavailableError(
                    "PaddleOCR requires EVIDENCE_OCR_MODEL_DIR with local det/ and rec/ models."
                )
            try:
                paddle_module = import_module("paddleocr")
            except ImportError as exc:
                raise OcrEngineUnavailableError(
                    "PaddleOCR is unavailable; install the `ocr-paddle` project extra."
                ) from exc
            try:
                runtime = paddle_module.PaddleOCR(
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    device="cpu",
                    text_detection_model_dir=str(model_dir / "det"),
                    text_recognition_model_dir=str(model_dir / "rec"),
                )
            except Exception as exc:
                raise OcrEngineUnavailableError(
                    "PaddleOCR could not initialize its local models."
                ) from exc
        self._runtime = runtime

    def extract(self, page_image: bytes, page_number: int) -> list[TextBox]:
        image, width, height = _read_image(page_image)
        try:
            numpy = import_module("numpy")
        except ImportError as exc:
            raise OcrEngineUnavailableError("PaddleOCR requires NumPy.") from exc
        try:
            results = self._runtime.predict(numpy.asarray(image))
        except Exception as exc:
            raise OcrProcessingError("PaddleOCR failed to process a page.") from exc
        boxes: list[TextBox] = []
        for result in results or []:
            texts = result.get("rec_texts", [])
            scores = result.get("rec_scores", [])
            bounds = result.get("rec_boxes", [])
            for text, confidence, box in zip(texts, scores, bounds, strict=False):
                boxes.append(
                    _text_box(box, str(text), float(confidence), page_number, width, height)
                )
        return boxes


def ocr_engine_factory(settings: Settings) -> EngineFactory:
    """Build a lazy engine factory so module imports remain optional and mockable."""
    if settings.evidence_ocr_engine == "rapidocr":
        return RapidOcrEngine
    return partial(PaddleOcrEngine, model_dir=settings.evidence_ocr_model_dir)


class OcrPageProcessor:
    """Run page OCR on a bounded worker pool and return boxes in page order."""

    def __init__(
        self,
        engine_factory: EngineFactory,
        *,
        workers: int,
        timeout_seconds: float,
    ) -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._engine_factory = engine_factory
        self._timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="docextract-ocr",
        )
        self._thread_engines = threading.local()
        self._closed = False

    async def extract_pages(self, pages: Sequence[DecodedPage]) -> list[TextBox]:
        """OCR only raster-required pages, preserving deterministic document order."""
        if self._closed:
            raise RuntimeError("OCR page processor is closed")
        work = [page for page in pages if page.requires_ocr]
        if not work:
            return []
        loop = asyncio.get_running_loop()
        futures = [loop.run_in_executor(self._executor, self._extract_page, page) for page in work]
        try:
            groups = await asyncio.wait_for(
                asyncio.gather(*futures), timeout=self._timeout_seconds
            )
        except TimeoutError as exc:
            for future in futures:
                future.cancel()
            raise OcrTimeoutError("OCR exceeded the configured time limit.") from exc
        return [box for group in groups for box in group]

    def close(self) -> None:
        """Stop accepting work; already-running native inference may finish in background."""
        if not self._closed:
            self._closed = True
            self._executor.shutdown(wait=False, cancel_futures=True)

    def _extract_page(self, page: DecodedPage) -> list[TextBox]:
        if page.raster_png is None:
            raise OcrProcessingError(f"Page {page.page} has no raster image for OCR.")
        engine = getattr(self._thread_engines, "engine", None)
        if engine is None:
            engine = self._engine_factory()
            self._thread_engines.engine = engine
        try:
            return engine.extract(page.raster_png, page.page)
        except OcrError:
            raise
        except Exception as exc:
            raise OcrProcessingError(f"OCR failed on page {page.page}.") from exc

    def __enter__(self) -> OcrPageProcessor:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _read_image(data: bytes) -> tuple[Image.Image, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            return rgb, width, height
    except Exception as exc:
        raise OcrProcessingError("OCR input is not a readable raster image.") from exc


def _text_box(
    polygon: Any,
    text: str,
    confidence: float,
    page: int,
    width: int,
    height: int,
) -> TextBox:
    coordinates = _as_points(polygon)
    if not coordinates or not text.strip():
        raise OcrProcessingError("OCR engine returned malformed text evidence.")
    x0 = _clamp(min(x for x, _ in coordinates) / width)
    y0 = _clamp(min(y for _, y in coordinates) / height)
    x1 = _clamp(max(x for x, _ in coordinates) / width)
    y1 = _clamp(max(y for _, y in coordinates) / height)
    if x0 >= x1 or y0 >= y1:
        raise OcrProcessingError("OCR engine returned an invalid bounding box.")
    return TextBox(
        page=page,
        text=text,
        bbox=(x0, y0, x1, y1),
        source="ocr",
        ocr_confidence=_clamp(confidence),
    )


def _as_points(value: Any) -> list[tuple[float, float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    flat = cast(Sequence[Any], value)
    if len(flat) == 4 and all(isinstance(item, (int, float)) for item in flat):
        return [(float(flat[0]), float(flat[1])), (float(flat[2]), float(flat[3]))]
    points: list[tuple[float, float]] = []
    try:
        for point in flat:
            if hasattr(point, "tolist"):
                point = point.tolist()
            coordinates = cast(Sequence[Any], point)
            if len(coordinates) >= 2:
                points.append((float(coordinates[0]), float(coordinates[1])))
    except (TypeError, ValueError, IndexError) as exc:
        raise OcrProcessingError("OCR engine returned malformed coordinates.") from exc
    if len(points) == 2:
        (x0, y0), (x1, y1) = points
        return [(x0, y0), (x1, y1)]
    return points


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))
