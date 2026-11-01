"""Environment-backed application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and the local .env file."""

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
