# CPU image: RapidOCR's ONNX models ship in its locked wheel, so startup needs no model download.
FROM python:3.12-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    EVIDENCE_OCR_ENGINE=rapidocr

RUN pip install --no-cache-dir uv==0.9.13
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "docextract.main:app", "--host", "0.0.0.0", "--port", "8000"]
