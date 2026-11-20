"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from docextract.api.errors import ApiErrorResponse

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Indicates that the API process is responding to requests."""

    status: str = Field(description='Service status; currently always "ok" on HTTP 200.')


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API health",
    description=(
        "Returns the process health status. This is a liveness check, not a provider check."
    ),
    response_description="The API process is responding.",
    responses={500: {"model": ApiErrorResponse, "description": "Unexpected server error."}},
)
def health_check() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")
