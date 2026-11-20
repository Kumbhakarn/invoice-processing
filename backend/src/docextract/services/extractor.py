"""AI document extraction with OpenAI-first and Gemini fallback."""

import asyncio
import base64
import json
import logging
import math
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from google import genai
from google.genai import types
from openai import OpenAI
from openai.types.responses.response_input_param import ResponseInputParam

from docextract.core.config import Settings, get_settings
from docextract.core.request_context import get_request_id
from docextract.schemas import InvoiceExtractionData
from docextract.schemas_evidence import EvidenceProviderResponse, RawFieldText
from docextract.services.prompt_template import (
    SYSTEM_PROMPT,
    build_evidence_user_prompt,
    build_user_prompt,
)
from docextract.services.usage import CostEstimate, ProviderUsage, calculate_cost, reported_usage

logger = logging.getLogger(__name__)


class ExtractionNotConfiguredError(RuntimeError):
    """Raised when neither AI provider has an API key configured."""


class ExtractionProviderError(RuntimeError):
    """Raised when all configured AI providers fail to extract the document."""

    def __init__(self, message: str, category: str = "provider-error") -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class ProviderCallResult:
    data: InvoiceExtractionData
    usage: ProviderUsage
    raw_fields: tuple[RawFieldText, ...] = ()
    field_logprobs: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    model: str
    duration_ms: float
    outcome: str
    usage: ProviderUsage
    cost: CostEstimate
    retry_count: int = 0
    fallback_used: bool = False


@dataclass(frozen=True)
class ExtractionResult:
    data: InvoiceExtractionData
    attempts: tuple[ProviderAttempt, ...]
    raw_fields: tuple[RawFieldText, ...] = ()
    field_logprobs: tuple[tuple[str, float], ...] = ()


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
) -> ProviderCallResult:
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
    return ProviderCallResult(response.output_parsed, reported_usage(response, "OpenAI"))


def _extract_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    settings: Settings,
) -> ProviderCallResult:
    """Use Gemini JSON schema output to extract the uploaded document."""
    if settings.gemini_api_key is None:
        raise ExtractionNotConfiguredError("GEMINI_API_KEY is not configured")

    response = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=60_000),
    ).models.generate_content(
        model=settings.gemini_model,
        contents=cast(
            Any,
            [
                build_user_prompt(),
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=InvoiceExtractionData,
        ),
    )
    if response.text is None:
        raise ValueError("Gemini returned no extraction data")
    return ProviderCallResult(
        InvoiceExtractionData.model_validate_json(response.text), reported_usage(response, "Gemini")
    )


def _extract_evidence_with_openai(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    settings: Settings,
) -> ProviderCallResult:
    """Return values and proposed raw text, with optional field-aligned token scores."""
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
                    {"type": "input_text", "text": build_evidence_user_prompt()},
                    document_content,
                ],
            },
        ],
    )
    response = OpenAI(api_key=settings.openai_api_key, timeout=60.0).responses.parse(
        model=settings.openai_model,
        input=response_input,
        text_format=EvidenceProviderResponse,
        include=["message.output_text.logprobs"],
    )
    parsed = response.output_parsed
    if parsed is None:
        raise ValueError("OpenAI returned no parsed evidence extraction data")
    return ProviderCallResult(
        data=parsed.data,
        usage=reported_usage(response, "OpenAI"),
        raw_fields=tuple(parsed.raw_fields),
        field_logprobs=tuple(_field_logprobs(response, parsed.data).items()),
    )


def _extract_evidence_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    settings: Settings,
) -> ProviderCallResult:
    """Return values and proposed raw text from Gemini's structured response."""
    if settings.gemini_api_key is None:
        raise ExtractionNotConfiguredError("GEMINI_API_KEY is not configured")
    response = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=60_000),
    ).models.generate_content(
        model=settings.gemini_model,
        contents=cast(
            Any,
            [
                build_evidence_user_prompt(),
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=EvidenceProviderResponse,
        ),
    )
    if response.text is None:
        raise ValueError("Gemini returned no evidence extraction data")
    parsed = EvidenceProviderResponse.model_validate_json(response.text)
    return ProviderCallResult(
        data=parsed.data,
        usage=reported_usage(response, "Gemini"),
        raw_fields=tuple(parsed.raw_fields),
    )


def _field_logprobs(response: object, data: InvoiceExtractionData) -> dict[str, float]:
    """Average output-token probabilities only where tokens align to a field value."""
    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text:
        return {}
    token_records: list[tuple[str, float]] = []
    output = getattr(response, "output", ())
    for message in output:
        for content in getattr(message, "content", ()):
            for item in getattr(content, "logprobs", ()) or ():
                token = getattr(item, "token", None)
                logprob = getattr(item, "logprob", None)
                if isinstance(token, str) and isinstance(logprob, (int, float)):
                    token_records.append((token, float(logprob)))
    if not token_records or "".join(token for token, _ in token_records) != output_text:
        return {}

    positions: list[tuple[int, int, float]] = []
    offset = 0
    for token, logprob in token_records:
        positions.append((offset, offset + len(token), logprob))
        offset += len(token)
    values = _flatten_values(data)
    scores: dict[str, float] = {}
    for field_name, value in values.items():
        if value is None:
            continue
        serialized = json.dumps(value, ensure_ascii=False)
        start = output_text.find(serialized)
        if start < 0:
            continue
        end = start + len(serialized)
        selected = [logprob for left, right, logprob in positions if left < end and right > start]
        if selected:
            scores[field_name] = sum(math.exp(item) for item in selected) / len(selected)
    return scores


def _flatten_values(data: InvoiceExtractionData) -> dict[str, object]:
    values: dict[str, object] = {}
    for field_name in InvoiceExtractionData.model_fields:
        value = getattr(data, field_name)
        if field_name == "line_items":
            for index, item in enumerate(value or []):
                for item_field in item.__class__.model_fields:
                    values[f"line_items[{index}].{item_field}"] = getattr(item, item_field)
        else:
            values[field_name] = value
    return values


async def extract_document_with_usage(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    *,
    include_raw: bool = False,
) -> ExtractionResult:
    """Try OpenAI first, then fall back to Gemini on any provider error."""
    settings = get_settings()
    providers: list[tuple[str, Callable[[], ProviderCallResult]]] = []
    if settings.openai_api_key:
        providers.append(
            (
                "OpenAI",
                lambda: (
                    _extract_evidence_with_openai(file_bytes, mime_type, filename, settings)
                    if include_raw
                    else _extract_with_openai(file_bytes, mime_type, filename, settings)
                ),
            )
        )
    if settings.gemini_api_key:
        providers.append(
            (
                "Gemini",
                lambda: (
                    _extract_evidence_with_gemini(file_bytes, mime_type, settings)
                    if include_raw
                    else _extract_with_gemini(file_bytes, mime_type, settings)
                ),
            )
        )
    if not providers:
        raise ExtractionNotConfiguredError(
            "Configure OPENAI_API_KEY, GEMINI_API_KEY, or both in backend/.env"
        )

    errors: list[str] = []
    categories: list[str] = []
    attempts: list[ProviderAttempt] = []
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
            if isinstance(result, InvoiceExtractionData):
                result = ProviderCallResult(result, ProviderUsage())
            duration_ms = round((time.perf_counter() - provider_started_at) * 1000, 2)
            cost = calculate_cost(
                provider_name,
                model_name,
                result.usage,
                settings.provider_pricing_json,
                settings.provider_pricing_version,
            )
            attempts.append(
                ProviderAttempt(
                    provider_name,
                    model_name,
                    duration_ms,
                    "success",
                    result.usage,
                    cost,
                    fallback_used=bool(attempts),
                )
            )
            logger.info(
                "AI provider attempt completed",
                extra={
                    "event": "provider_attempt_finished",
                    "request_id": get_request_id(),
                    "provider": provider_name,
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "outcome": "success",
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "total_tokens": result.usage.total_tokens,
                    "usage_source": result.usage.source,
                    "cost_usd": str(cost.amount_usd) if cost.amount_usd is not None else None,
                    "pricing_version": cost.pricing_version,
                    "fallback_used": bool(attempts[:-1]),
                    "retry_count": 0,
                },
            )
            return ExtractionResult(
                result.data,
                tuple(attempts),
                result.raw_fields,
                result.field_logprobs,
            )
        except Exception as error:
            category = _provider_error_category(error)
            duration_ms = round((time.perf_counter() - provider_started_at) * 1000, 2)
            empty_usage = ProviderUsage()
            empty_cost = calculate_cost(
                provider_name,
                model_name,
                empty_usage,
                settings.provider_pricing_json,
                settings.provider_pricing_version,
            )
            attempts.append(
                ProviderAttempt(
                    provider_name,
                    model_name,
                    duration_ms,
                    "failure",
                    empty_usage,
                    empty_cost,
                    fallback_used=bool(attempts),
                )
            )
            logger.warning(
                "AI provider attempt failed",
                extra={
                    "event": "provider_attempt_failed",
                    "request_id": get_request_id(),
                    "provider": provider_name,
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "outcome": "failure",
                    "error_category": category,
                    "error_type": type(error).__name__,
                    "provider_error_status": getattr(error, "status_code", None),
                    "provider_error_code": getattr(error, "code", None),
                    "provider_error_param": getattr(error, "param", None),
                    "stack_trace": traceback.format_tb(error.__traceback__),
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "usage_source": "unavailable",
                    "cost_usd": None,
                    "pricing_version": empty_cost.pricing_version,
                    "fallback_used": bool(attempts[:-1]),
                    "retry_count": 0,
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


async def extract_document_data(
    file_bytes: bytes,
    mime_type: str,
    filename: str,
) -> InvoiceExtractionData:
    """Backward-compatible extraction entry point returning only invoice data."""
    result = await extract_document_with_usage(file_bytes, mime_type, filename)
    return result.data
