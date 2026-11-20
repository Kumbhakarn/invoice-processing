"""Create document extraction persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_document_extractions"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the extraction records table."""
    op.create_table(
        "document_extractions",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "provider_attempts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_document_extractions_file_size"),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="ck_document_extractions_input_tokens",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="ck_document_extractions_output_tokens",
        ),
        sa.PrimaryKeyConstraint("file_id", name="pk_document_extractions"),
        sa.UniqueConstraint("storage_path", name="uq_document_extractions_storage_path"),
    )
    op.create_index(
        "ix_document_extractions_trace_id",
        "document_extractions",
        ["trace_id"],
    )


def downgrade() -> None:
    """Drop extraction records."""
    op.drop_index("ix_document_extractions_trace_id", table_name="document_extractions")
    op.drop_table("document_extractions")
