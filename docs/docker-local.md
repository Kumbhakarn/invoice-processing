# Run DocExtract locally with Docker Compose

This setup runs the frontend, FastAPI backend, and PostgreSQL locally. PostgreSQL data and uploaded documents persist in named Docker volumes. The backend uses the bundled RapidOCR models, so it does not download OCR models at runtime.

## Prerequisites

- Docker Desktop for Windows with the Compose plugin
- An OpenAI or Gemini API key for real extraction requests

## Configure and start

Run these commands in PowerShell from the repository root:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose build
docker compose up -d
```

Set `POSTGRES_PASSWORD` in `.env` before building or starting. Add at least one provider key before submitting documents for extraction. Compose builds the frontend with mock mode disabled; the application does not make provider calls during image builds.

The database health check must pass before Alembic runs. The backend starts only after the migration service completes successfully and the database is healthy.

## Check status and logs

```powershell
docker compose ps
docker compose logs -f frontend backend migrate postgres
Invoke-WebRequest http://localhost:8080/api/health
```

Open the app at `http://localhost:8080`. The API is served through the same origin under `/api`; nginx allows uploads up to 12 MiB and waits up to 360 seconds for API responses.

## Stop and preserve local data

```powershell
docker compose down
```

This stops and removes the containers while retaining the PostgreSQL and document storage volumes. Start again with `docker compose up -d`.

To remove the containers and permanently delete both volumes, including the local database and uploaded documents, run:

```powershell
docker compose down --volumes
```

Keep `.env` local. Do not commit provider keys or the database password.
