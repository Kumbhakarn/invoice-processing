# DocExtract frontend

React/Vite workspace for invoice review. See [the user guide](../docs/frontend-user-guide.md), [architecture](../docs/frontend-architecture.md), and [testing notes](../docs/frontend-testing.md).

## Prerequisites

- Node.js 20 or newer and npm.
- For real mode only: the backend and its local PostgreSQL/OCR/provider configuration.

## Run in mock mode

From `frontend/` in PowerShell:

```powershell
npm ci
npm run dev
```

Mock mode is the default (`VITE_USE_MOCK=true`); it does not call providers. Open the local Vite URL printed in the terminal.

## Run with the real backend

Terminal 1, from `backend/`:

```powershell
uv run uvicorn docextract.main:app --reload
```

Terminal 2, from `frontend/`:

```powershell
$env:VITE_USE_MOCK = "false"
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`; no CORS changes are needed. **Uploads call AI providers and may incur charges.** Upload one document at a time when manually checking real mode.

## Environment and commands

`VITE_USE_MOCK` defaults to true when unset. `npm run gen:api` reads the running backend OpenAPI URL; pass a local schema path as `npm run gen:api -- ./openapi.json` for offline generation. Commands: `dev`, `build`, `typecheck`, `lint`, `test`, `test:e2e`.

If local dependencies are absent, run `npm ci`. If real requests fail, check the backend terminal, readiness at `http://127.0.0.1:8000/api/ready`, and that `VITE_USE_MOCK=false` was set before Vite started. Local development only; no authentication is implemented. Do not expose this service publicly.
