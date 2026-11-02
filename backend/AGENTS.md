Python 3.12, FastAPI, Pydantic v2, uv, Ruff, pytest, mypy.
Layout: src/docextract/{api,core,services,schemas.py}.
Commands: uv sync | uv run ruff check . | uv run pytest | uv run mypy src
Extraction: OpenAI first, Gemini fallback. Provider calls must be async, have timeouts, and be mockable in tests.