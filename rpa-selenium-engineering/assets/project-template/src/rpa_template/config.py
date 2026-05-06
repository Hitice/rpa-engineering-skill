"""Runtime configuration loaded from environment variables.

All values are externalized; no hardcoded URLs, credentials, timeouts, paths
or feature flags. ``state_db_path`` and ``lock_path`` are optional: when
omitted the runtime falls back to in-memory equivalents (no persistence,
no single-instance enforcement).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RPA_",
        extra="ignore",
        case_sensitive=False,
    )

    process_name: str = Field(default="rpa-template")
    target_url: HttpUrl
    username: SecretStr
    password: SecretStr

    browser: Literal["chrome", "firefox", "edge"] = "chrome"
    headless: bool = True

    default_timeout_s: float = Field(default=15.0, gt=0)
    submit_timeout_s: float = Field(default=30.0, gt=0)

    retry_attempts: int = Field(default=3, ge=1)
    retry_initial_delay_s: float = Field(default=0.5, gt=0)
    retry_max_delay_s: float = Field(default=5.0, gt=0)

    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum cross-run attempts before promoting an item to DEAD_LETTER.",
    )

    state_db_path: Path | None = None
    lock_path: Path | None = None
    lock_timeout_s: float = Field(default=10.0, ge=0)

    artifacts_dir: Path = Path("./artifacts")
    log_level: str = "INFO"

    dry_run: bool = False


def load_settings() -> Settings:
    """Build a :class:`Settings` instance from the current environment.

    Required fields (``target_url``, ``username``, ``password``) are populated
    from environment variables at instantiation time, which mypy cannot see.
    """
    return Settings()  # type: ignore[call-arg]
