"""Configuration path tests."""

from pathlib import Path

from docextract.core.config import BACKEND_ROOT, Settings


def test_env_file_path_is_anchored_to_backend() -> None:
    """Loading settings must not depend on the shell's current directory."""
    env_file = Settings.model_config["env_file"]

    assert env_file == BACKEND_ROOT / ".env"
    assert Path(env_file).is_absolute()
