"""FastAPI application factory."""

from fastapi import FastAPI

from docextract.api.routes.extract import router as extract_router
from docextract.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="DocExtract API",
        summary="Invoice processing and extraction API",
        version="0.1.0",
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(extract_router, prefix="/api")
    return application
