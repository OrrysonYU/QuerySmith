"""Capped, timeout-bound read-only query execution."""

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

from pydantic import BaseModel, Field

from querysmith.execution.errors import (
    DatabaseErrorClass,
    ExecutionError,
    normalize_database_exception,
)


class Cursor(Protocol):
    @property
    def description(self) -> Any: ...
    async def execute(self, sql: str) -> Any: ...
    async def fetchmany(self, size: int) -> list[Any]: ...


class Connection(Protocol):
    def execute(self, sql: str) -> Any: ...


class ExecutionLimits(BaseModel):
    timeout_seconds: float = Field(30, gt=0, le=120)
    max_rows: int = Field(1000, ge=1)
    max_bytes: int = Field(5_000_000, ge=1024)


class ExecutionOutcome(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    bytes_returned: int = 0
    duration_ms: float = 0
    error: ExecutionError | None = None


class RowStream(Protocol):
    columns: list[str]

    def __aiter__(self) -> AsyncIterator[list[Any]]: ...


class QueryExecutor:
    """The sole model-SQL execution boundary."""

    def __init__(self, stream_factory: Callable[[str], RowStream]) -> None:
        self._stream_factory = stream_factory

    async def execute(self, sql: str, limits: ExecutionLimits) -> ExecutionOutcome:
        started = time.perf_counter()
        try:
            async with asyncio.timeout(limits.timeout_seconds):
                stream = self._stream_factory(sql)
                rows: list[list[Any]] = []
                size = 0
                truncated = False
                async for row in stream:
                    encoded = len(json.dumps(row, default=str).encode())
                    if len(rows) >= limits.max_rows or size + encoded > limits.max_bytes:
                        truncated = True
                        break
                    rows.append(row)
                    size += encoded
                return ExecutionOutcome(
                    columns=stream.columns,
                    rows=rows,
                    row_count=len(rows),
                    truncated=truncated,
                    bytes_returned=size,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
        except TimeoutError:
            return ExecutionOutcome(
                duration_ms=(time.perf_counter() - started) * 1000,
                error=ExecutionError(
                    category=DatabaseErrorClass.TIMEOUT, safe_message="Query execution timed out."
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return ExecutionOutcome(
                duration_ms=(time.perf_counter() - started) * 1000,
                error=normalize_database_exception(exc),
            )
