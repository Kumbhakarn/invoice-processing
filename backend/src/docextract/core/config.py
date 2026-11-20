"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Settings loaded from environment variables and the local .env file."""

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_model: str = "gpt-6-luna"
    gemini_model: str = "gemini-3.8-flash"
    max_upload_size_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 50
    max_image_width: int = 10_000
    max_image_height: int = 10_000
    evidence_render_dpi: Annotated[int, Field(ge=36, le=600)] = 200
    evidence_text_layer_min_chars: Annotated[int, Field(ge=1)] = 20
    evidence_ocr_engine: Literal["rapidocr", "paddleocr"] = "rapidocr"
    evidence_ocr_workers: Annotated[int, Field(ge=1, le=8)] = 2
    evidence_ocr_timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 30
    evidence_ocr_model_dir: Path | None = None
    evidence_match_threshold: Annotated[float, Field(gt=0, le=1)] = 0.82
    evidence_match_ambiguity_margin: Annotated[float, Field(ge=0, le=1)] = 0.05
    log_level: str = "INFO"
    provider_pricing_json: str = "{}"
    provider_pricing_version: str = "unconfigured"
    database_url: str | None = None
    document_storage_dir: Path = BACKEND_ROOT / "data" / "documents"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Treat an empty DATABASE_URL as disabled persistence."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
