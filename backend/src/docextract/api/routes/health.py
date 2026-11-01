"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Service health response."""

    status: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")
