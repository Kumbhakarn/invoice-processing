"""Request-scoped context shared by API and service loggers."""

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_file_id: ContextVar[str | None] = ContextVar("file_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    """Set the current request ID and return its reset token."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request ID that was active before this request."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request ID for the current execution context."""
    return _request_id.get()


def set_file_id(file_id: str) -> Token[str | None]:
    """Set the current upload file ID and return its reset token."""
    return _file_id.set(file_id)


def get_file_id() -> str | None:
    """Return the current upload file ID, if the request contains an upload."""
    return _file_id.get()
