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
- Invoice schemas, extraction services, and storage will be added as the product is built.
