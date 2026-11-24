FROM ghcr.io/astral-sh/uv:0.9.13 AS uv

FROM python:3.12-slim AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --no-editable
RUN uv run --no-sync python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR()"

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EVIDENCE_OCR_ENGINE=rapidocr \
    DOCUMENT_STORAGE_DIR=/data/documents
WORKDIR /app
RUN groupadd --system --gid 10001 docextract \
    && useradd --system --uid 10001 --gid docextract --home-dir /home/docextract docextract \
    && mkdir -p /data/documents \
    && chown -R docextract:docextract /data /home/docextract
COPY --from=builder --chown=docextract:docextract /opt/venv /opt/venv
COPY --from=builder --chown=docextract:docextract /app/src ./src
COPY --from=builder --chown=docextract:docextract /app/migrations ./migrations
COPY --from=builder --chown=docextract:docextract /app/alembic.ini ./alembic.ini
USER docextract
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["uvicorn", "docextract.main:app", "--host", "0.0.0.0", "--port", "8000"]
