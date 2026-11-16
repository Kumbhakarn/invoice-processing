"""Centralized API error types and response handlers."""

import logging
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


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_error_handlers(application: FastAPI) -> None:
    """Register API-wide handlers so failures share a stable response shape."""

    @application.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        return _error_response(error.status_code, error.code, error.message)

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
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
        return _error_response(error.status_code, code, message)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        logger.info("Request validation failed: %s", error.errors())
        return _error_response(422, "INVALID_REQUEST", "The request is invalid.")

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API error (%s) at %s",
            type(error).__name__,
            request.url.path,
        )
        return _error_response(
            500,
            "INTERNAL_SERVER_ERROR",
            "An unexpected server error occurred.",
        )
