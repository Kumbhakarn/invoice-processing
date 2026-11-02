# DocExtract
Invoice/export-document extraction app. Monorepo: backend/ (FastAPI) and frontend/ (React).
The API contract lives in docs/api-contract.md and is the source of truth; do not change
it without updating that file and telling me.

## Rules
- Make small, reviewable changes; explain what you changed.
- Run lint and tests before finishing.
- Never commit secrets; .env stays local.