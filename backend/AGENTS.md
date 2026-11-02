# Backend guidance

DocExtract backend: Python 3.12, FastAPI, Pydantic v2, `uv`, Ruff, pytest, and mypy.

## Layout and commands

- Source: `src/docextract/{api,core,services,schemas.py}`.
- Tests: `tests/`.
- Run `uv sync`, `uv run ruff check .`, `uv run pytest`, and `uv run mypy src` from this directory as relevant to the change.
- Do not install dependencies unless required by an approved implementation task.

## Current API and behavior

- `GET /api/health` reports service availability.
- `POST /api/extract` accepts PDF, JPEG, or PNG invoice/export documents and returns `InvoiceExtractionData` from `src/docextract/schemas.py`.
- The configured upload limit is `MAX_UPLOAD_SIZE_BYTES`, defaulting to 10 MiB. The route reads no more than limit + 1 bytes, rejects empty files with 400 and oversized files with 413.
- `MAX_PDF_PAGES` defaults to 50. `MAX_IMAGE_WIDTH` and `MAX_IMAGE_HEIGHT` default to 10,000 pixels. Exceeding these resource limits returns 413.
- The route checks file signatures/basic structure and consistency between file contents, filename extension, and declared MIME type. Malformed supported files return 400; unsupported formats or mismatches return 415.
- Format checks are lightweight integrity checks, not full document decoding. Upload size validation occurs after multipart parsing; application reads remain bounded.
- Extraction tries OpenAI first and Gemini as fallback. Preserve provider timeouts and testability.
- PDF page counting uses `pypdf` without rendering. Image dimensions are read from PNG/JPEG headers; avoid decoding images into full-resolution pixel buffers for validation.

## Change rules

- Make small, scoped changes. Avoid unrelated refactors and unnecessary dependencies.
- Do not change `InvoiceExtractionData`, extraction prompts, provider integration, or the public API contract unless requested or approved by the user. If the API contract changes, update root `docs/api-contract.md` and tell the user.
- Mock provider calls in endpoint/service tests; do not make tests depend on live AI credentials or services.
- Do not read, print, or overwrite secrets in `.env`. Put safe configuration names/defaults in `.env.example`.
- The latest completed work covers bounded uploads and lightweight file content validation. Wait for the user's review and approval before starting another feature.
