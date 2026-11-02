"""AI document extraction with OpenAI-first and Gemini fallback."""

import asyncio
import base64
import logging
from collections.abc import Callable
from typing import cast

from google import genai
from google.genai import types
from openai import OpenAI
from openai.types.responses.response_input_param import ResponseInputParam

from docextract.core.config import Settings, get_settings
from docextract.schemas import InvoiceExtractionData
from docextract.services.prompt_template import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class ExtractionNotConfiguredError(RuntimeError):
    """Raised when neither AI provider has an API key configured."""


class ExtractionProviderError(RuntimeError):
    """Raised when all configured AI providers fail to extract the document."""


def _extract_with_openai(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    settings: Settings,
) -> InvoiceExtractionData:
    """Use OpenAI structured output parsing to extract the uploaded document."""
    if settings.openai_api_key is None:
        raise ExtractionNotConfiguredError("OPENAI_API_KEY is not configured")

    data_url = f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('ascii')}"
    if mime_type == "application/pdf":
        document_content: dict[str, str] = {
            "type": "input_file",
            "filename": filename,
            "file_data": data_url,
        }
    else:
        document_content = {"type": "input_image", "image_url": data_url}

    response_input = cast(
        ResponseInputParam,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": build_user_prompt()},
                    document_content,
                ],
            },
        ],
    )
    response = OpenAI(api_key=settings.openai_api_key, timeout=60.0).responses.parse(
        model=settings.openai_model,
        input=response_input,
        text_format=InvoiceExtractionData,
    )
    if response.output_parsed is None:
        raise ValueError("OpenAI returned no parsed extraction data")
    return response.output_parsed


def _extract_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    settings: Settings,
) -> InvoiceExtractionData:
    """Use Gemini JSON schema output to extract the uploaded document."""
    if settings.gemini_api_key is None:
        raise ExtractionNotConfiguredError("GEMINI_API_KEY is not configured")

    response = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=60_000),
    ).models.generate_content(
        model=settings.gemini_model,
        contents=[
            build_user_prompt(),
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=InvoiceExtractionData,
        ),
    )
    if response.text is None:
        raise ValueError("Gemini returned no extraction data")
    return InvoiceExtractionData.model_validate_json(response.text)


async def extract_document_data(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
) -> InvoiceExtractionData:
    """Try OpenAI first, then fall back to Gemini on any provider error."""
    settings = get_settings()
    providers: list[tuple[str, Callable[[], InvoiceExtractionData]]] = []
    if settings.openai_api_key:
        providers.append(
            ("OpenAI", lambda: _extract_with_openai(file_bytes, mime_type, filename, settings))
        )
    if settings.gemini_api_key:
        providers.append(("Gemini", lambda: _extract_with_gemini(file_bytes, mime_type, settings)))
    if not providers:
        raise ExtractionNotConfiguredError(
            "Configure OPENAI_API_KEY, GEMINI_API_KEY, or both in backend/.env"
        )

    errors: list[str] = []
    for provider_name, provider_call in providers:
        try:
            return await asyncio.to_thread(provider_call)
        except Exception as error:
            logger.warning("%s document extraction failed", provider_name)
            logger.debug("%s extraction error: %s", provider_name, error, exc_info=True)
            errors.append(f"{provider_name}: {type(error).__name__}")

    raise ExtractionProviderError(
        "All configured document extraction providers failed: " + "; ".join(errors)
    )
