"""Validated environment-driven application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    environment: Literal["local", "ci", "staging", "production"] = "local"
    request_deadline_seconds: int = Field(120, ge=1, le=600)
    sync_wait_seconds: int = Field(25, ge=0, le=120)
    max_concurrent_jobs: int = Field(8, ge=1, le=128)


class LLMSettings(BaseSettings):
    provider: Literal["mock", "glm", "openai_compat"] = "mock"
    model: str = "mock"
    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout_seconds: int = Field(30, ge=1, le=120)
    max_calls_per_query: int = Field(10, ge=1, le=30)
    max_tokens_per_query: int = Field(60_000, ge=1_000)


class DataSourceSettings(BaseSettings):
    app_database_url: SecretStr = SecretStr("postgresql+asyncpg://querysmith@localhost/querysmith")
    default_source: str = "chinook"
    source_database_url: SecretStr | None = None
    allowed_tables_csv: str = "artist,album,genre,media_type,employee,customer,invoice,track,invoice_line,playlist,playlist_track"
    blocked_columns_csv: str = "customer.email"
    statement_timeout_ms: int = Field(30_000, ge=100, le=120_000)
    max_rows: int = Field(1_000, ge=1, le=100_000)
    max_bytes: int = Field(5_000_000, ge=1_024)


class PolicySettings(BaseSettings):
    require_limit: bool = True
    reject_select_star: bool = True
    max_rows: int = Field(1_000, ge=1, le=100_000)


class ObservabilitySettings(BaseSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    otlp_endpoint: str | None = None
    metrics_enabled: bool = True


class Settings(BaseSettings):
    """Aggregate settings loaded with nested ``QS_`` environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="QS_", env_nested_delimiter="__", env_file=".env", extra="ignore"
    )
    core: CoreSettings = Field(default_factory=lambda: CoreSettings())
    llm: LLMSettings = Field(default_factory=lambda: LLMSettings())
    datasource: DataSourceSettings = Field(default_factory=lambda: DataSourceSettings())
    policy: PolicySettings = Field(default_factory=lambda: PolicySettings())
    observability: ObservabilitySettings = Field(default_factory=lambda: ObservabilitySettings())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
