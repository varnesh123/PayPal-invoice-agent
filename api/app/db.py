"""Supabase / PostgreSQL database client.

Phase 1: wires the backend to Supabase using environment variables.
The client is created lazily so the health endpoint can respond without
a live database connection (important while Supabase is not yet provisioned).
"""

from functools import lru_cache
from typing import Optional

from supabase import create_client, Client
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are read from a `.env` file (not committed) or the shell
    environment. See `.env.example` for the full list of variables.
    """

    app_name: str = "invoice-collection-agent"
    app_env: str = "development"
    debug: bool = True

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    secret_key: str = "change-me-in-production"

    database_url: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_anon_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_supabase() -> Optional[Client]:
    """Return a Supabase client, or None if credentials are not configured.

    Returning None (rather than raising) keeps the health endpoint and the
    rest of the app importable before Supabase has been provisioned.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_database_url() -> Optional[str]:
    return get_settings().database_url
