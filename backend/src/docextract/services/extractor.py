"""AI document extraction with OpenAI-first and Gemini fallback."""

import asyncio
import base64
import logging
import time
import traceback
from collections.abc import Callable
from typing import cast

from google import genai
from google.genai import types
from openai import OpenAI
from openai.types.responses.response_input_param import ResponseInputParam

from docextract.core.config import Settings, get_settings
from docextract.core.request_context import get_request_id
from docextract.schemas import InvoiceExtractionData
from docextract.services.prompt_template import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class ExtractionNotConfiguredError(RuntimeError):
    """Raised when neither AI provider has an API key configured."""


class ExtractionProviderError(RuntimeError):
    """Raised when all configured AI providers fail to extract the document."""

    def __init__(self, message: str, category: str = "provider-error") -> None:
        super().__init__(message)
        self.category = category


def _provider_error_category(error: Exception) -> str:
    """Classify common SDK failures for useful diagnostics without retrying."""
    name = type(error).__name__.lower()
    message = str(error).lower()
    status_code = getattr(error, "status_code", None)
    if "auth" in name or "permission" in name or status_code == 401 or status_code == 403:
        return "authentication"
    if "quota" in name or "billing" in name or "insufficient_quota" in message:
        return "quota/billing"
    if "ratelimit" in name or "rate_limit" in name or status_code == 429:
        return "rate-limit"
    if isinstance(error, (TimeoutError, asyncio.TimeoutError)) or "timeout" in name:
        return "timeout"
    if "connection" in name or "network" in name:
        return "network"
    if isinstance(status_code, int) and status_code >= 500:
        return "transient-server"
    if isinstance(error, (ValueError, TypeError)):
        return "invalid-response"
    return "provider-error"


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
    categories: list[str] = []
    for provider_name, provider_call in providers:
        model_name = settings.openai_model if provider_name == "OpenAI" else settings.gemini_model
        provider_started_at = time.perf_counter()
        logger.info(
            "AI provider attempt started",
            extra={
                "event": "provider_attempt_started",
                "request_id": get_request_id(),
                "provider": provider_name,
                "model": model_name,
                "outcome": "started",
            },
        )
        try:
            result = await asyncio.to_thread(provider_call)
            logger.info(
                "AI provider attempt completed",
                extra={
                    "event": "provider_attempt_finished",
                    "request_id": get_request_id(),
                    "provider": provider_name,
                    "model": model_name,
                    "duration_ms": round((time.perf_counter() - provider_started_at) * 1000, 2),
                    "outcome": "success",
                },
            )
            return result
        except Exception as error:
            category = _provider_error_category(error)
            logger.warning(
                "AI provider attempt failed",
                extra={
                    "event": "provider_attempt_failed",
                    "request_id": get_request_id(),
                    "provider": provider_name,
                    "model": model_name,
                    "duration_ms": round((time.perf_counter() - provider_started_at) * 1000, 2),
                    "outcome": "failure",
                    "error_category": category,
                    "error_type": type(error).__name__,
                    "stack_trace": traceback.format_tb(error.__traceback__),
                },
            )
            errors.append(f"{provider_name}: {type(error).__name__}")
            categories.append(category)

    category_priority = ("timeout", "authentication", "rate-limit", "invalid-response")
    category = next((item for item in category_priority if item in categories), "provider-error")
    raise ExtractionProviderError(
        "All configured document extraction providers failed: " + "; ".join(errors),
        category,
    )
