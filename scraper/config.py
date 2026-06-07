from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://arbitrage:arbitrage@localhost:5432/arbitrage"
    timezone: str = "Europe/Sofia"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    http_timeout: float = 30.0
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
