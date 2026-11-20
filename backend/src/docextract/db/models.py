"""Persisted document extraction metadata and results."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from docextract.db.base import Base


class DocumentExtractionRecord(Base):
    """One successfully processed upload and its AI result and reported usage."""

    __tablename__ = "document_extractions"
    __table_args__ = (
        Index("ix_document_extractions_trace_id", "trace_id"),
        CheckConstraint("file_size_bytes >= 0", name="ck_document_extractions_file_size"),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_document_extractions_input_tokens",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_document_extractions_output_tokens",
        ),
        UniqueConstraint("storage_path", name="uq_document_extractions_storage_path"),
    )

    file_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    trace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_attempts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
