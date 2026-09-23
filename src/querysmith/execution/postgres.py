"""Streaming PostgreSQL row source for the controlled executor."""

from collections.abc import AsyncIterator, Callable
from typing import Any

from querysmith.execution.connection_manager import ConnectionManager


class PostgresRowStream:
    def __init__(self, manager: ConnectionManager, source: str, sql: str) -> None:
        self._manager = manager
        self._source = source
        self._sql = sql
        self.columns: list[str] = []

    def __aiter__(self) -> AsyncIterator[list[Any]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[list[Any]]:
        async with (
            self._manager.acquire(self._source) as connection,
            connection.transaction(readonly=True),
        ):
            statement = await connection.prepare(self._sql)
            self.columns = [attribute.name for attribute in statement.get_attributes()]
            async for record in statement.cursor(prefetch=100):
                yield list(record)


def postgres_stream_factory(
    manager: ConnectionManager, source: str
) -> Callable[[str], PostgresRowStream]:
    return lambda sql: PostgresRowStream(manager, source, sql)
