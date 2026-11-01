"""Application entry point."""

import uvicorn

from docextract.api.app import create_app

app = create_app()


def run() -> None:
    """Run the development server."""
    uvicorn.run("docextract.main:app", host="127.0.0.1", port=8000, reload=True)
