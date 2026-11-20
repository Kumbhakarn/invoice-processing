"""PostgreSQL persistence and local document storage tests."""

import asyncio
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from docextract.api import app as app_module
from docextract.core.config import Settings
from docextract.db import service as db_service
from docextract.db.session import DatabaseResources, check_database_connection, create_database
from docextract.db.storage import store_document
from docextract.schemas import InvoiceExtractionData
from docextract.services.extractor import ExtractionResult, ProviderAttempt
from docextract.services.usage import CostEstimate, ProviderUsage


def test_empty_database_url_disables_persistence() -> None:
    assert Settings(database_url=" ").database_url is None


def test_document_storage_uses_utc_date_and_file_id(tmp_path: Path) -> None:
    file_id = uuid4()
    uploaded_at = datetime(2025, 1, 2, 1, 30, tzinfo=timezone(timedelta(hours=2)))

    relative_path = store_document(
        tmp_path,
        file_id,
        "application/pdf",
        uploaded_at,
        b"document-bytes",
    )

    assert relative_path == f"2025/01/01/{file_id}.pdf"
    assert (tmp_path / relative_path).read_bytes() == b"document-bytes"


def _attempt(
    provider: str,
    outcome: str,
    usage: ProviderUsage,
) -> ProviderAttempt:
    return ProviderAttempt(
        provider=provider,
        model=f"{provider.lower()}-model",
        duration_ms=12.5,
        outcome=outcome,
        usage=usage,
        cost=CostEstimate(None, "unconfigured"),
        fallback_used=provider == "Gemini",
    )


def test_persist_extraction_stores_json_and_provider_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    file_id = uuid4()
    trace_id = uuid4()
    uploaded_at = datetime.now(UTC)
    processed_at = datetime.now(UTC)
    result = ExtractionResult(
        data=InvoiceExtractionData(invoice_number="INV-42"),
        attempts=(
            _attempt("OpenAI", "failure", ProviderUsage()),
            _attempt("Gemini", "success", ProviderUsage(20, 8, 28)),
        ),
    )

    def store(*args: object) -> str:
        captured["storage_args"] = args
        return "2025/01/01/document.pdf"

    async def save(*args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(db_service, "store_document", store)
    monkeypatch.setattr(db_service, "save_extraction", save)
    database = DatabaseResources(
        engine=cast(AsyncEngine, object()),
        sessions=cast(async_sessionmaker[AsyncSession], object()),
    )

    asyncio.run(
        db_service.persist_extraction(
            database,
            storage_root=tmp_path,
            file_id=file_id,
            trace_id=trace_id,
            uploaded_at=uploaded_at,
            processed_at=processed_at,
            content_type="application/pdf",
            file_bytes=b"invoice",
            extracted_data=result.data.model_dump(mode="json"),
            provider_attempts=db_service.extraction_attempt_usage(result),
        )
    )

    assert captured["file_id"] == file_id
    assert captured["trace_id"] == trace_id
    assert captured["extracted_data"]["invoice_number"] == "INV-42"
    assert captured["input_tokens"] is None
    assert captured["output_tokens"] is None
    assert captured["provider_attempts"][1]["input_tokens"] == 20
    assert captured["provider_attempts"][1]["output_tokens"] == 8
    assert captured["provider_attempts"][0]["usage_source"] == "unavailable"


def test_database_write_failure_removes_stored_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    removed: list[str] = []

    def store(*args: object) -> str:
        return "2025/01/01/document.pdf"

    async def fail_save(*args: object, **kwargs: object) -> None:
        raise OperationalError("insert", {}, RuntimeError("database unavailable"))

    def delete(root: Path, relative_path: str) -> None:
        removed.append(relative_path)

    monkeypatch.setattr(db_service, "store_document", store)
    monkeypatch.setattr(db_service, "save_extraction", fail_save)
    monkeypatch.setattr(db_service, "delete_stored_document", delete)
    database = DatabaseResources(
        engine=cast(AsyncEngine, object()),
        sessions=cast(async_sessionmaker[AsyncSession], object()),
    )

    with pytest.raises(db_service.PersistenceFailureError):
        asyncio.run(
            db_service.persist_extraction(
                database,
                storage_root=tmp_path,
                file_id=uuid4(),
                trace_id=uuid4(),
                uploaded_at=datetime.now(UTC),
                processed_at=datetime.now(UTC),
                content_type="application/pdf",
                file_bytes=b"invoice",
                extracted_data={},
                provider_attempts=[],
            )
        )

    assert removed == ["2025/01/01/document.pdf"]


def test_postgresql_connection_when_test_database_is_configured() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set TEST_DATABASE_URL to run the PostgreSQL connectivity integration test")

    async def check() -> None:
        database = create_database(database_url)
        try:
            await check_database_connection(database.engine)
        finally:
            await database.engine.dispose()

    asyncio.run(check())


def test_application_lifespan_disposes_database_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EngineStub:
        disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    engine = EngineStub()
    database = DatabaseResources(
        engine=cast(AsyncEngine, engine),
        sessions=cast(async_sessionmaker[AsyncSession], object()),
    )
    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: Settings(database_url="postgresql+asyncpg://unused"),
    )
    monkeypatch.setattr(app_module, "create_database", lambda _: database)
    application = app_module.create_app()

    with TestClient(application):
        assert application.state.database is database

    assert engine.disposed
