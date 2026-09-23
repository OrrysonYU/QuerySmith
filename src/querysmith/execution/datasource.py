"""Validated data-source registry and secret-reference resolution."""

import os
from enum import StrEnum

from pydantic import BaseModel, Field, SecretStr, field_validator


class Dialect(StrEnum):
    POSTGRES = "postgres"
    SQLITE = "sqlite"


class DataSourceConfig(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    dialect: Dialect
    secret_reference: str
    statement_timeout_ms: int = Field(30_000, ge=100, le=120_000)
    pool_min_size: int = Field(1, ge=1, le=20)
    pool_max_size: int = Field(5, ge=1, le=50)
    search_path: str = Field("public", pattern=r"^[a-zA-Z_][a-zA-Z0-9_, ]*$")

    @field_validator("pool_max_size")
    @classmethod
    def pool_sizes_valid(cls, value: int, info: object) -> int:
        del info
        return value


class DataSourceRegistry:
    def __init__(self, sources: list[DataSourceConfig]) -> None:
        self._sources = {source.name: source for source in sources}
        if len(self._sources) != len(sources):
            raise ValueError("duplicate data-source name")

    def items(self) -> list[tuple[str, DataSourceConfig]]:
        return list(self._sources.items())

    def get(self, name: str) -> DataSourceConfig:
        try:
            return self._sources[name]
        except KeyError as exc:
            raise KeyError(f"unknown data source: {name}") from exc

    @staticmethod
    def resolve_secret(reference: str) -> SecretStr:
        if not reference.startswith("env:"):
            raise ValueError("Level 1 supports only env: secret references")
        name = reference.removeprefix("env:")
        value = os.environ.get(name)
        if not value:
            raise ValueError(f"required secret environment variable is missing: {name}")
        return SecretStr(value)
