import asyncio
from typing import Any, ClassVar

import pytest

from querysmith.execution.errors import DatabaseErrorClass
from querysmith.execution.executor import ExecutionLimits, QueryExecutor


class Stream:
    columns: ClassVar[list[str]] = ["value"]

    def __init__(self, rows: list[list[Any]], delay: float = 0) -> None:
        self.rows = rows
        self.delay = delay

    def __aiter__(self) -> "Stream":
        self.iterator = iter(self.rows)
        return self

    async def __anext__(self) -> list[Any]:
        if self.delay:
            await asyncio.sleep(self.delay)
        try:
            return next(self.iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@pytest.mark.asyncio
async def test_executor_enforces_row_and_byte_caps() -> None:
    rows = [["x" * 100], ["y" * 100], ["z" * 100]]
    outcome = await QueryExecutor(lambda sql: Stream(rows)).execute(
        "SELECT", ExecutionLimits(max_rows=2, max_bytes=1024)
    )
    assert outcome.row_count == 2 and outcome.truncated
    large_rows = [["x" * 800], ["y" * 800]]
    byte_limited = await QueryExecutor(lambda sql: Stream(large_rows)).execute(
        "SELECT", ExecutionLimits(max_rows=10, max_bytes=1024)
    )
    assert byte_limited.bytes_returned <= 1024 and byte_limited.truncated


@pytest.mark.asyncio
async def test_executor_timeout_is_safe_and_classified() -> None:
    outcome = await QueryExecutor(lambda sql: Stream([[1]], delay=0.1)).execute(
        "SELECT", ExecutionLimits(timeout_seconds=0.01)
    )
    assert outcome.error and outcome.error.category is DatabaseErrorClass.TIMEOUT
