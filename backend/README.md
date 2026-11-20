# DocExtract backend

FastAPI service for invoice and export-document extraction.

## Run locally

From this directory, install the project and development tools, then start Uvicorn:

```powershell
uv sync --dev
uv run uvicorn docextract.main:app --reload
```

The interactive OpenAPI UI is at <http://127.0.0.1:8000/docs>; the generated schema is at
<http://127.0.0.1:8000/openapi.json>. Check the service with:

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

## Endpoints

- `GET /api/health` checks that the API process is responding.
- `POST /api/extract` accepts a PDF, JPEG, or PNG invoice as multipart form data and returns
  the nullable invoice extraction schema.
- `POST /api/extract/evidence` is an interim PDF/image extraction route with field evidence.
- `POST /api/validate` checks an `InvoiceExtractionData` JSON body without changing it.

There is no authentication requirement in the current backend. The full request/response
contract, limits, environment variables, provider behavior, and error codes are documented
in [`../docs/api-contract.md`](../docs/api-contract.md).

Example invoice upload from this directory:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/extract `
  -F "file=@invoice.pdf;type=application/pdf"
```

## Configuration

Copy `.env.example` to `.env` and configure at least one AI provider key for extraction.
Keep `.env` local and do not commit it. The environment-variable reference in the API
contract lists all supported settings and defaults.

## Project layout

- `src/docextract/api` contains the FastAPI app and routes.
- `src/docextract/schemas.py` defines the invoice extraction data model.
- `src/docextract/services` contains extraction, evidence, and validation services.
- `tests` contains backend tests.
- `../docs/api-contract.md` is the public API contract source of truth.
