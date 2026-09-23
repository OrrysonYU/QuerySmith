"""Semaphore-bounded in-process job runner with durable state transitions."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from querysmith.agent.state import QueryStatus
from querysmith.persistence.jobs import JobRecord, JobRepository


class JobRunner:
    def __init__(
        self,
        repository: JobRepository,
        execute: Callable[[JobRecord], Awaitable[dict[str, Any]]],
        max_concurrency: int = 8,
    ) -> None:
        self._repository = repository
        self._execute = execute
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def start(self) -> int:
        return await self._repository.reconcile_running()

    async def submit(self, job: JobRecord) -> JobRecord:
        persisted = await self._repository.create(job)
        if persisted.id not in self._tasks and persisted.status is QueryStatus.QUEUED:
            self._tasks[persisted.id] = asyncio.create_task(
                self._run(persisted), name=f"querysmith-{persisted.id}"
            )
        return persisted

    async def _run(self, job: JobRecord) -> None:
        try:
            async with self._semaphore:
                await self._repository.update_status(job.id, QueryStatus.RUNNING)
                result = await self._execute(job)
                status = QueryStatus(str(result.get("status", QueryStatus.FAILED)))
                await self._repository.update_status(job.id, status, result)
        except asyncio.CancelledError:
            await self._repository.update_status(
                job.id, QueryStatus.CANCELLED, {"status": QueryStatus.CANCELLED}
            )
            raise
        except Exception:
            await self._repository.update_status(
                job.id,
                QueryStatus.FAILED,
                {"status": QueryStatus.FAILED, "failure": "internal_error"},
            )
        finally:
            self._tasks.pop(job.id, None)

    async def cancel(self, job_id: UUID, user_id: UUID) -> bool:
        if not await self._repository.request_cancel(job_id, user_id):
            return False
        task = self._tasks.get(job_id)
        if task:
            task.cancel()
        return True

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
