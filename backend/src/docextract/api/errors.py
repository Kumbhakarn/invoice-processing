"""Centralized API error types and response handlers."""

import logging
import traceback
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """An expected API failure with a stable public code and message."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    trace_id = getattr(request.state, "trace_id", request_id)
    file_id = getattr(request.state, "file_id", None)
    request.state.error_code = code
    error = {"code": code, "message": message}
    if request_id is not None:
        error["request_id"] = request_id
    headers = {"X-Request-ID": request_id} if request_id is not None else {}
    if trace_id is not None:
        headers["X-Trace-ID"] = trace_id
    if file_id is not None:
        headers["X-File-ID"] = file_id
    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers=headers or None,
    )


def register_error_handlers(application: FastAPI) -> None:
    """Register API-wide handlers so failures share a stable response shape."""

    @application.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return _error_response(request, error.status_code, error.code, error.message)

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        mapping: Mapping[int, tuple[str, str]] = {
            400: ("INVALID_REQUEST", "The request could not be processed."),
            404: ("NOT_FOUND", "The requested resource was not found."),
            405: ("METHOD_NOT_ALLOWED", "The request method is not allowed."),
            413: ("FILE_TOO_LARGE", "The request exceeds the allowed size."),
            415: ("UNSUPPORTED_FORMAT", "The uploaded file format is not supported."),
            422: ("INVALID_REQUEST", "The request is invalid."),
        }
        code, message = mapping.get(
            error.status_code,
            ("HTTP_ERROR", "The request could not be completed."),
        )
        return _error_response(request, error.status_code, code, message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        logger.info(
            "request validation failed",
            extra={
                "event": "request_validation_failed",
                "request_id": getattr(request.state, "request_id", None),
                "endpoint": request.url.path,
                "error_category": "INVALID_REQUEST",
            },
        )
        return _error_response(request, 422, "INVALID_REQUEST", "The request is invalid.")

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "unhandled API exception",
            extra={
                "event": "unhandled_exception",
                "request_id": getattr(request.state, "request_id", None),
                "endpoint": request.url.path,
                "http_status": 500,
                "outcome": "failure",
                "error_category": "INTERNAL_SERVER_ERROR",
                "error_type": type(error).__name__,
                "stack_trace": traceback.format_tb(error.__traceback__),
            },
        )
        return _error_response(
            request,
            500,
            "INTERNAL_SERVER_ERROR",
            "An unexpected server error occurred.",
        )
