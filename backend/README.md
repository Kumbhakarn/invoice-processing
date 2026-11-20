# DocExtract backend

FastAPI service for the DocExtract invoice processing application.

## Getting started

Install dependencies and start the local API from this directory:

```powershell
uv sync --dev
uv run uvicorn docextract.main:app --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.
The health endpoint is `GET /api/health`.

PostgreSQL persistence is optional. To enable it, set `DATABASE_URL` in `.env` to a
`postgresql+asyncpg` connection URL, install the dependencies with `uv sync`, then run
the migration command from this directory:

```powershell
uv run alembic upgrade head
```

When configured, successful requests to either extraction endpoint store the original
document below `DOCUMENT_STORAGE_DIR/YYYY/MM/DD/` and save the extracted JSON, UTC
timestamps, and provider token usage in PostgreSQL. The default storage directory is `data/documents`;
document files and extracted invoice data are sensitive and should be included in local
backup and retention policies. `GET /api/ready` checks database readiness. The existing
`GET /api/health` remains a process liveness check.

`POST /api/extract` accepts a multipart form upload with a `file` field containing a
PDF or image. It returns the configured invoice fields for document type and number,
buyer/exporter/consignee/notify-party names and addresses, shipment destinations and
ports, shipping marks, line items, currency and payment terms, amount in words, and
weights. OpenAI is tried first; Gemini is used as a fallback when configured.

Set `OPENAI_API_KEY` and/or `GEMINI_API_KEY` in `backend/.env`. When both are set,
OpenAI is attempted first and Gemini is used if the OpenAI request fails, including
quota or rate limit errors. Model names can be overridden with `OPENAI_MODEL` and
`GEMINI_MODEL`. Copy `.env.example` to `.env` as a starting point.

## Project layout

- `src/docextract/api` contains the FastAPI app and HTTP routes.
- `tests` contains backend tests.
- `src/docextract/db` contains database models, session handling, and local document persistence.
- `migrations` contains Alembic schema revisions.
