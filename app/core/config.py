"""Application configuration loaded from .env via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app settings. Values are read from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "Tanilink"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Storage
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (evaluated once per process)."""
    return Settings()
