"""Small persistence operations without a separate repository layer."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docextract.db.models import DocumentExtractionRecord


async def save_extraction(
    sessions: async_sessionmaker[AsyncSession],
    *,
    file_id: UUID,
    trace_id: UUID,
    uploaded_at: datetime,
    processed_at: datetime,
    content_type: str,
    file_size_bytes: int,
    storage_path: str,
    extracted_data: dict[str, Any],
    input_tokens: int | None,
    output_tokens: int | None,
    provider_attempts: list[dict[str, Any]],
) -> None:
    """Persist one extraction record in a single transaction."""
    record = DocumentExtractionRecord(
        file_id=file_id,
        trace_id=trace_id,
        uploaded_at=uploaded_at,
        processed_at=processed_at,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        storage_path=storage_path,
        extracted_data=extracted_data,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider_attempts=provider_attempts,
    )
    async with sessions.begin() as session:
        session.add(record)
