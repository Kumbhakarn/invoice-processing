"""Safe structured logging using only the Python standard library."""

import json
import logging
from datetime import UTC, datetime
from logging import LogRecord
from typing import Any

from docextract.core.request_context import get_request_id

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
    "stack_trace",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "usage_source",
    "cost_usd",
    "pricing_version",
    "fallback_used",
    "retry_count",
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
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        return json.dumps(entry, separators=(",", ":"), default=str)


def configure_logging(level_name: str) -> None:
    """Set the application log level and install its JSON console handler once."""
    root_logger = logging.getLogger()
    level = getattr(logging, level_name.upper(), logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO
    root_logger.setLevel(level)

    if not any(getattr(handler, "_docextract_json", False) for handler in root_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler._docextract_json = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
