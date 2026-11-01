"""AI-backed invoice extraction with provider fallback."""

import asyncio
import base64
import logging
from collections.abc import Callable

from google import genai
from google.genai import types
from openai import OpenAI

from docextract.api.schemas.invoice import InvoiceExtractionResponse
from docextract.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_EXTRACTION_INSTRUCTIONS = (
    "Extract invoice data from the supplied document. Return only information visible in the "
    "document. Use null for unavailable scalar values and an empty list when there are no "
    "line items. Do not infer missing values. Return dates in YYYY-MM-DD format."
)


class ExtractionNotConfiguredError(RuntimeError):
    """Raised when neither AI provider has an API key configured."""


class ExtractionProviderError(RuntimeError):
    """Raised when all configured AI providers fail to extract the invoice."""


def _extract_with_openai(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    settings: Settings,
) -> InvoiceExtractionResponse:
    """Extract structured invoice data with OpenAI's Pydantic parsing helper."""
    if settings.openai_api_key is None:
        raise ExtractionNotConfiguredError("OPENAI_API_KEY is not configured")

    encoded_file = base64.b64encode(file_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded_file}"
    if mime_type == "application/pdf":
        document_content: dict[str, str] = {
            "type": "input_file",
            "filename": filename,
            "file_data": data_url,
        }
    else:
        document_content = {"type": "input_image", "image_url": data_url}

    client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
    response = client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": _EXTRACTION_INSTRUCTIONS},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Extract the invoice fields."},
                    document_content,
                ],
            },
        ],
        text_format=InvoiceExtractionResponse,
    )
    if response.output_parsed is None:
        raise ValueError("OpenAI returned no parsed invoice data")
    return response.output_parsed


def _extract_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    settings: Settings,
) -> InvoiceExtractionResponse:
    """Extract structured invoice data with Gemini's JSON schema response mode."""
    if settings.gemini_api_key is None:
        raise ExtractionNotConfiguredError("GEMINI_API_KEY is not configured")

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=60_000),
    )
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            _EXTRACTION_INSTRUCTIONS,
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InvoiceExtractionResponse,
        ),
    )
    if response.text is None:
        raise ValueError("Gemini returned no invoice data")
    return InvoiceExtractionResponse.model_validate_json(response.text)


async def extract_invoice_data(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
) -> InvoiceExtractionResponse:
    """Try OpenAI first, then Gemini when configured, including on quota errors."""
    settings = get_settings()
    providers: list[tuple[str, Callable[[], InvoiceExtractionResponse]]] = []
    if settings.openai_api_key:
        providers.append(
            (
                "OpenAI",
                lambda: _extract_with_openai(file_bytes, mime_type, filename, settings),
            )
        )
    if settings.gemini_api_key:
        providers.append(("Gemini", lambda: _extract_with_gemini(file_bytes, mime_type, settings)))
    if not providers:
        raise ExtractionNotConfiguredError(
            "Configure OPENAI_API_KEY, GEMINI_API_KEY, or both in the backend .env file"
        )

    errors: list[str] = []
    for provider_name, provider_call in providers:
        try:
            return await asyncio.to_thread(provider_call)
        except Exception as error:
            logger.warning("%s invoice extraction failed", provider_name)
            logger.debug("%s extraction error: %s", provider_name, error, exc_info=True)
            errors.append(f"{provider_name}: {type(error).__name__}")

    raise ExtractionProviderError(
        "All configured invoice extraction providers failed: " + "; ".join(errors)
    )
