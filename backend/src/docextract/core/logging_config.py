"""Safe structured logging using only the Python standard library."""

import json
import logging
from datetime import UTC, datetime
from logging import LogRecord
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from docextract.core.config import BACKEND_ROOT
from docextract.core.request_context import get_file_id, get_request_id

_EXTRA_FIELDS = (
    "event",
    "endpoint",
    "http_status",
    "method",
    "provider",
    "model",
    "duration_ms",
    "upload_size_bytes",
    "outcome",
    "error_category",
    "error_type",
    "provider_error_status",
    "provider_error_code",
    "provider_error_param",
    "stack_trace",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "usage_source",
    "cost_usd",
    "pricing_version",
    "fallback_used",
    "retry_count",
    "trace_id",
    "file_id",
    "page_count",
    "text_box_count",
    "ocr_page_count",
    "field_count",
    "located_count",
    "ambiguous_count",
    "unavailable_count",
    "confidence_high_count",
    "confidence_medium_count",
    "confidence_low_count",
    "confidence_unavailable_count",
)


class JsonLogFormatter(logging.Formatter):
    """Serialize a fixed set of safe structured fields as one JSON object."""

    def format(self, record: LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "trace_id": getattr(record, "trace_id", None) or get_request_id(),
            "file_id": getattr(record, "file_id", None) or get_file_id(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        return json.dumps(entry, separators=(",", ":"), default=str)


def configure_logging(level_name: str) -> None:
    """Set the app log level and install structured console and rotating file handlers."""
    root_logger = logging.getLogger()
    level = getattr(logging, level_name.upper(), logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO
    root_logger.setLevel(level)

    if not any(getattr(handler, "_docextract_console", False) for handler in root_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler._docextract_console = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)

    if not any(getattr(handler, "_docextract_file", False) for handler in root_logger.handlers):
        log_path = Path(BACKEND_ROOT) / "app.log"
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonLogFormatter())
        file_handler._docextract_file = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)
