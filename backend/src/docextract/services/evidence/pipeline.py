"""End-to-end evidence extraction orchestration without changing `/api/extract`."""

from __future__ import annotations

import asyncio
import io
import logging
import time

from PIL import Image

from docextract.core.config import Settings
from docextract.schemas_evidence import (
    EvidenceExtractionResponse,
    EvidenceMetadata,
    ProviderUsageMetadata,
)
from docextract.services.evidence.confidence import score_field_confidence
from docextract.services.evidence.mapper import map_extraction_fields
from docextract.services.evidence.matcher import ground_raw_fields, match_invoice_fields
from docextract.services.evidence.ocr import (
    OcrEngineUnavailableError,
    OcrPageProcessor,
    OcrProcessingError,
    OcrTimeoutError,
    ocr_engine_factory,
)
from docextract.services.evidence.pages import decode_document, page_metadata
from docextract.services.evidence.types import DecodedDocument, DecodedPage
from docextract.services.extractor import extract_document_with_usage

logger = logging.getLogger(__name__)


async def extract_evidence_document(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    settings: Settings,
    *,
    validation_ms: float = 0.0,
) -> EvidenceExtractionResponse:
    """Decode, OCR, extract, ground, match, and map one document for review."""
    total_started = time.perf_counter()
    text_layer_started = time.perf_counter()
    document = await asyncio.to_thread(decode_document, file_bytes, mime_type, settings)
    text_layer_ms = _elapsed_ms(text_layer_started)

    text_boxes = [box for page in document.pages for box in page.text_boxes]
    ocr_failed = False
    ocr_started = time.perf_counter()
    ocr_pages = [page for page in document.pages if page.requires_ocr]
    if ocr_pages:
        try:
            with OcrPageProcessor(
                ocr_engine_factory(settings),
                workers=settings.evidence_ocr_workers,
                timeout_seconds=settings.evidence_ocr_timeout_seconds,
            ) as processor:
                text_boxes.extend(await processor.extract_pages(ocr_pages))
        except OcrTimeoutError:
            raise
        except OcrEngineUnavailableError:
            raise
        except OcrProcessingError as exc:
            # Text-layer pages and AI extraction can still succeed when OCR has a page failure.
            ocr_failed = True
            logger.warning(
                "OCR failed for evidence document",
                extra={"event": "evidence_ocr_failed", "error_type": type(exc).__name__},
            )
    ocr_ms = _elapsed_ms(ocr_started)

    provider_bytes, provider_mime, provider_filename = await _provider_input(
        file_bytes,
        mime_type,
        filename,
        document,
        settings.evidence_render_dpi,
    )
    llm_started = time.perf_counter()
    extraction = await extract_document_with_usage(
        provider_bytes,
        provider_mime,
        provider_filename,
        include_raw=True,
    )
    llm_ms = _elapsed_ms(llm_started)

    matching_started = time.perf_counter()
    grounded_raw = ground_raw_fields(extraction.data, extraction.raw_fields, text_boxes)
    field_evidence = match_invoice_fields(
        extraction.data,
        text_boxes,
        settings,
        ocr_failed=ocr_failed,
    )
    field_evidence = [
        item.model_copy(update={"raw": grounded_raw.get(item.field)}) for item in field_evidence
    ]
    field_evidence = score_field_confidence(
        extraction.data,
        field_evidence,
        text_boxes,
        dict(extraction.field_logprobs),
        settings,
    )
    matching_ms = _elapsed_ms(matching_started)
    usage = [
        ProviderUsageMetadata(
            provider=attempt.provider,
            model=attempt.model,
            input_tokens=attempt.usage.input_tokens,
            output_tokens=attempt.usage.output_tokens,
            reasoning_tokens=attempt.usage.reasoning_tokens,
        )
        for attempt in extraction.attempts
    ]
    return EvidenceExtractionResponse(
        data=extraction.data,
        fields=map_extraction_fields(extraction.data, field_evidence),
        pages=page_metadata(document),
        meta=EvidenceMetadata(
            timings_ms={
                "validation": round(validation_ms, 2),
                "text_layer": text_layer_ms,
                "ocr": ocr_ms,
                "llm": llm_ms,
                "matching": matching_ms,
                "total": _elapsed_ms(total_started) + validation_ms,
            },
            provider_usage=usage,
        ),
    )


async def _provider_input(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    document: DecodedDocument,
    dpi: int,
) -> tuple[bytes, str, str]:
    if mime_type == "application/pdf":
        return file_bytes, mime_type, filename
    pdf_bytes = await asyncio.to_thread(_raster_pages_to_pdf, document.pages, dpi)
    return pdf_bytes, "application/pdf", f"{filename.rsplit('.', maxsplit=1)[0]}.pdf"


def _raster_pages_to_pdf(pages: tuple[DecodedPage, ...], dpi: int) -> bytes:
    images: list[Image.Image] = []
    try:
        for page in pages:
            if page.raster_png is None:
                raise ValueError("Rasterized page image is unavailable")
            with Image.open(io.BytesIO(page.raster_png)) as image:
                images.append(image.convert("RGB"))
        if not images:
            raise ValueError("Image document has no pages")
        output = io.BytesIO()
        first, *rest = images
        first.save(
            output,
            format="PDF",
            save_all=True,
            append_images=rest,
            resolution=dpi,
        )
        return output.getvalue()
    finally:
        for raster in images:
            raster.close()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
