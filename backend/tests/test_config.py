"""Configuration path tests."""

from pathlib import Path

import pytest

from docextract.core.config import BACKEND_ROOT, Settings


def test_env_file_path_is_anchored_to_backend() -> None:
    """Loading settings must not depend on the shell's current directory."""
    env_file = Settings.model_config["env_file"]

    assert env_file == BACKEND_ROOT / ".env"
    assert Path(env_file).is_absolute()


def test_resource_limits_are_configurable_through_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_PDF_PAGES", "12")
    monkeypatch.setenv("MAX_IMAGE_WIDTH", "2400")
    monkeypatch.setenv("MAX_IMAGE_HEIGHT", "1800")

    settings = Settings(_env_file=None)

    assert settings.max_pdf_pages == 12
    assert settings.max_image_width == 2400
    assert settings.max_image_height == 1800
