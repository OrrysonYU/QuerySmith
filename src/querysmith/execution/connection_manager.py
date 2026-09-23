"""Lifecycle-managed PostgreSQL pools and read-only SQLite connections."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
import asyncpg
from pydantic import SecretStr

from querysmith.execution.datasource import DataSourceRegistry, Dialect


class ConnectionManager:
    def __init__(
        self,
        registry: DataSourceRegistry,
        secret_resolver: Callable[[str], SecretStr] | None = None,
    ) -> None:
        self._registry = registry
        self._resolve_secret = secret_resolver or registry.resolve_secret
        self._pg_pools: dict[str, asyncpg.Pool[Any]] = {}

    async def start(self) -> None:
        for name, source in self._registry.items():
            if source.dialect is not Dialect.POSTGRES:
                continue
            dsn = self._resolve_secret(source.secret_reference).get_secret_value()
            self._pg_pools[name] = await asyncpg.create_pool(
                dsn,
                min_size=source.pool_min_size,
                max_size=source.pool_max_size,
                server_settings={
                    "default_transaction_read_only": "on",
                    "statement_timeout": str(source.statement_timeout_ms),
                    "search_path": source.search_path,
                },
            )

    @asynccontextmanager
    async def acquire(self, name: str) -> AsyncIterator[Any]:
        source = self._registry.get(name)
        if source.dialect is Dialect.POSTGRES:
            pool = self._pg_pools.get(name)
            if pool is None:
                raise RuntimeError("connection manager not started")
            async with pool.acquire() as connection:
                yield connection
            return
        path = self._resolve_secret(source.secret_reference).get_secret_value()
        uri = path if path.startswith("file:") else f"file:{path}?mode=ro"
        async with aiosqlite.connect(uri, uri=True) as connection:
            await connection.execute("PRAGMA query_only = ON")
            yield connection

    async def healthcheck(self, name: str) -> bool:
        try:
            async with self.acquire(name) as connection:
                await connection.fetchval("SELECT 1") if hasattr(
                    connection, "fetchval"
                ) else await connection.execute("SELECT 1")
            return True
        except (OSError, RuntimeError, asyncpg.PostgresError, aiosqlite.Error):
            return False

    async def close_all(self) -> None:
        for pool in self._pg_pools.values():
            await pool.close()
        self._pg_pools.clear()
