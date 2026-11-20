"""Health check endpoint."""

import logging

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from docextract.core.config import get_settings
from docextract.db.session import DatabaseResources, check_database_connection

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Service health response."""

    status: str


class ReadinessResponse(BaseModel):
    """Application and database readiness status."""

    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "Database is unavailable."}},
)
async def readiness_check(request: Request, response: Response) -> ReadinessResponse:
    """Report whether the API and configured PostgreSQL database can serve requests."""
    if not get_settings().database_url:
        response.status_code = 503
        return ReadinessResponse(status="not_ready", database="unavailable")

    database = getattr(request.app.state, "database", None)
    if not isinstance(database, DatabaseResources):
        response.status_code = 503
        return ReadinessResponse(status="not_ready", database="unavailable")
    try:
        await check_database_connection(database.engine)
    except SQLAlchemyError:
        logger.warning("database readiness check failed", extra={"event": "database_unavailable"})
        response.status_code = 503
        return ReadinessResponse(status="not_ready", database="unavailable")
    return ReadinessResponse(status="ready", database="ok")
