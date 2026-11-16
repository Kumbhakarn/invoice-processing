"""Request-scoped context shared by API and service loggers."""

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    """Set the current request ID and return its reset token."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request ID that was active before this request."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request ID for the current execution context."""
    return _request_id.get()
