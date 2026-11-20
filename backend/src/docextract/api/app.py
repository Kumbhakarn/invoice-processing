"""FastAPI application factory."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from docextract.api.errors import register_error_handlers
from docextract.api.routes.evidence import router as evidence_router
from docextract.api.routes.extract import router as extract_router
from docextract.api.routes.health import router as health_router
from docextract.api.routes.validate import router as validate_router
from docextract.core.config import get_settings
from docextract.core.logging_config import configure_logging
from docextract.core.request_context import reset_request_id, set_request_id

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(get_settings().log_level)
    application = FastAPI(
        title="DocExtract API",
        summary="Invoice processing and extraction API",
        version="0.1.0",
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(extract_router, prefix="/api")
    application.include_router(evidence_router, prefix="/api")
    application.include_router(validate_router, prefix="/api")
    register_error_handlers(application)

    @application.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        request.state.trace_id = request_id
        token = set_request_id(request_id)
        started_at = time.perf_counter()
        endpoint = request.url.path
        logger.info(
            "request received",
            extra={
                "event": "request_started",
                "request_id": request_id,
                "trace_id": request_id,
                "endpoint": endpoint,
                "method": request.method,
            },
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = request_id
            file_id = getattr(request.state, "file_id", None)
            if file_id is not None:
                response.headers["X-File-ID"] = file_id
            outcome = "success" if response.status_code < 400 else "failure"
            logger.info(
                "request completed",
                extra={
                    "event": "request_finished",
                    "request_id": request_id,
                    "trace_id": request_id,
                    "file_id": getattr(request.state, "file_id", None),
                    "endpoint": endpoint,
                    "method": request.method,
                    "http_status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "upload_size_bytes": getattr(request.state, "upload_size_bytes", None),
                    "outcome": outcome,
                    "error_category": getattr(request.state, "error_code", None),
                },
            )
            return response
        except Exception as error:
            logger.error(
                "request failed",
                extra={
                    "event": "request_finished",
                    "request_id": request_id,
                    "trace_id": request_id,
                    "file_id": getattr(request.state, "file_id", None),
                    "endpoint": endpoint,
                    "method": request.method,
                    "http_status": 500,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "upload_size_bytes": getattr(request.state, "upload_size_bytes", None),
                    "outcome": "failure",
                    "error_category": "INTERNAL_SERVER_ERROR",
                    "error_type": type(error).__name__,
                },
            )
            raise
        finally:
            reset_request_id(token)

    return application
