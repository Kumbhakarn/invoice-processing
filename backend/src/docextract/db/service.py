"""Database readiness and persistence for successful extraction requests."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from docextract.db.operations import save_extraction
from docextract.db.session import DatabaseResources, check_database_connection
from docextract.db.storage import delete_stored_document, store_document
from docextract.services.extractor import ExtractionResult

logger = logging.getLogger(__name__)


class DatabaseUnavailableError(RuntimeError):
    """Raised when required persistence storage is unavailable."""


class PersistenceFailureError(RuntimeError):
    """Raised when an extraction result cannot be committed to PostgreSQL."""


async def ensure_database_ready(database: DatabaseResources | None) -> DatabaseResources:
    """Verify a configured database before spending time on provider extraction."""
    if database is None:
        raise DatabaseUnavailableError("Database resources are not initialized")
    try:
        await check_database_connection(database.engine)
    except (OSError, SQLAlchemyError) as error:
        raise DatabaseUnavailableError("Database connection failed") from error
    return database


def _attempt_usage(attempts: ExtractionResult) -> list[dict[str, Any]]:
    return [
        {
            "provider": attempt.provider,
            "model": attempt.model,
            "outcome": attempt.outcome,
            "duration_ms": attempt.duration_ms,
            "fallback_used": attempt.fallback_used,
            "input_tokens": attempt.usage.input_tokens,
            "output_tokens": attempt.usage.output_tokens,
            "total_tokens": attempt.usage.total_tokens,
            "usage_source": (
                attempt.usage.source
                if attempt.usage.input_tokens is not None or attempt.usage.output_tokens is not None
                else "unavailable"
            ),
        }
        for attempt in attempts.attempts
    ]


async def persist_extraction(
    database: DatabaseResources,
    *,
    storage_root: Path,
    file_id: UUID,
    trace_id: UUID,
    uploaded_at: datetime,
    processed_at: datetime,
    content_type: str,
    file_bytes: bytes,
    extracted_data: dict[str, Any],
    provider_attempts: list[dict[str, Any]],
) -> None:
    """Store a successful input file and its extraction record consistently."""
    storage_path = await asyncio.to_thread(
        store_document,
        storage_root,
        file_id,
        content_type,
        uploaded_at,
        file_bytes,
    )
    try:
        await save_extraction(
            database.sessions,
            file_id=file_id,
            trace_id=trace_id,
            uploaded_at=uploaded_at,
            processed_at=processed_at,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            storage_path=storage_path,
            extracted_data=extracted_data,
            input_tokens=_aggregate_usage(provider_attempts, "input_tokens"),
            output_tokens=_aggregate_usage(provider_attempts, "output_tokens"),
            provider_attempts=provider_attempts,
        )
    except SQLAlchemyError as error:
        try:
            await asyncio.to_thread(delete_stored_document, storage_root, storage_path)
        except OSError:
            logger.exception(
                "could not remove local document after database write failed",
                extra={"event": "document_storage_cleanup_failed", "file_id": str(file_id)},
            )
        raise PersistenceFailureError("Database write failed") from error


def extraction_attempt_usage(result: ExtractionResult) -> list[dict[str, Any]]:
    """Serialize provider attempt usage without adding it to public API responses."""
    return _attempt_usage(result)


def evidence_attempt_usage(
    provider_usage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize usage metadata emitted by the evidence pipeline."""
    return [
        {
            **usage,
            "usage_source": (
                "provider_reported"
                if usage.get("input_tokens") is not None or usage.get("output_tokens") is not None
                else "unavailable"
            ),
        }
        for usage in provider_usage
    ]


def _aggregate_usage(
    attempts: list[dict[str, Any]],
    attribute: Literal["input_tokens", "output_tokens"],
) -> int | None:
    counts = [attempt.get(attribute) for attempt in attempts]
    if not counts or any(count is None for count in counts):
        return None
    return sum(count for count in counts if isinstance(count, int))
