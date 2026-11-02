# DocExtract

Invoice and export-document extraction app in a monorepo. The FastAPI backend is implemented; frontend guidance lives in `frontend/AGENTS.md`.

## Project rules

- Make small, reviewable changes and explain what changed.
- `docs/api-contract.md` is the source of truth for the public API. Update it and tell the user if a change to that contract is justified.
- Do not commit or expose secrets. `backend/.env` stays local; use `.env.example` for documented configuration names and defaults.
- Do not start another feature until the user has reviewed the current feature and approved the next work.
- Keep architecture simple. Avoid unnecessary dependencies, microservices, and unrelated refactors.
- Run the relevant tests and lint before finishing implementation work. Do not claim commands passed unless they were run.

## Current backend state

- Python 3.12, FastAPI, Pydantic v2, `uv`, Ruff, pytest, and mypy.
- Backend source layout: `backend/src/docextract/{api,core,services,schemas.py}`.
- `GET /api/health` and `POST /api/extract` are implemented.
- Extraction uses OpenAI first and Gemini as fallback. Keep provider calls asynchronous at the API boundary, timed out, and mockable in tests.
- Uploads are bounded by configurable `MAX_UPLOAD_SIZE_BYTES` (10 MiB default), read at most limit + 1 bytes, and reject empty uploads.
- Upload content validation supports PDF, JPEG, and PNG; it checks basic format structure and compares actual format with extension and MIME type. Unsupported types return 415; malformed supported files return 400; oversized uploads return 413.
- Invoice extraction response schema is in `backend/src/docextract/schemas.py`. Do not change it or extraction prompts/provider integration unless the user requests or approves that scope.
- Upload validation runs after multipart parsing. The endpoint bounds bytes read into application memory; request-body limits at the server/proxy layer are a separate concern.

## Backend commands

Run from `backend/`:

```powershell
uv sync
uv run ruff check .
uv run pytest
uv run mypy src
```
