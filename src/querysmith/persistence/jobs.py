"""Durable job repository contract with SQLAlchemy and deterministic memory implementations."""

import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.agent.state import QueryStatus
from querysmith.persistence.models import Query


class JobRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    question: str
    status: QueryStatus = QueryStatus.QUEUED
    result: dict[str, Any] | None = None
    conversation_id: UUID | None = None
    idempotency_key: str | None = None
    cancel_requested: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobRepository(Protocol):
    async def create(self, job: JobRecord) -> JobRecord: ...
    async def get(self, job_id: UUID, user_id: UUID) -> JobRecord | None: ...
    async def find_idempotent(self, user_id: UUID, key: str) -> JobRecord | None: ...
    async def update_status(
        self, job_id: UUID, status: QueryStatus, result: dict[str, Any] | None = None
    ) -> None: ...
    async def request_cancel(self, job_id: UUID, user_id: UUID) -> bool: ...
    async def reconcile_running(self) -> int: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[UUID, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: JobRecord) -> JobRecord:
        async with self._lock:
            if job.idempotency_key:
                existing = await self._find_idempotent_unlocked(job.user_id, job.idempotency_key)
                if existing:
                    return existing
            self._jobs[job.id] = job.model_copy(deep=True)
            return job

    async def get(self, job_id: UUID, user_id: UUID) -> JobRecord | None:
        job = self._jobs.get(job_id)
        return job.model_copy(deep=True) if job and job.user_id == user_id else None

    async def _find_idempotent_unlocked(self, user_id: UUID, key: str) -> JobRecord | None:
        return next(
            (
                job
                for job in self._jobs.values()
                if job.user_id == user_id and job.idempotency_key == key
            ),
            None,
        )

    async def find_idempotent(self, user_id: UUID, key: str) -> JobRecord | None:
        async with self._lock:
            job = await self._find_idempotent_unlocked(user_id, key)
            return job.model_copy(deep=True) if job else None

    async def update_status(
        self, job_id: UUID, status: QueryStatus, result: dict[str, Any] | None = None
    ) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            self._jobs[job_id] = job.model_copy(
                update={"status": status, "result": result, "updated_at": datetime.now(UTC)}
            )

    async def request_cancel(self, job_id: UUID, user_id: UUID) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.user_id != user_id:
                return False
            self._jobs[job_id] = job.model_copy(update={"cancel_requested": True})
            return True

    async def reconcile_running(self) -> int:
        count = 0
        async with self._lock:
            for job_id, job in list(self._jobs.items()):
                if job.status is QueryStatus.RUNNING:
                    self._jobs[job_id] = job.model_copy(
                        update={"status": QueryStatus.FAILED, "result": {"failure": "orphaned"}}
                    )
                    count += 1
        return count


class SqlJobRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, job: JobRecord) -> JobRecord:
        if job.idempotency_key:
            existing = await self.find_idempotent(job.user_id, job.idempotency_key)
            if existing:
                return existing
        async with self._sessions() as session, session.begin():
            session.add(
                Query(
                    id=job.id,
                    user_id=job.user_id,
                    question=job.question,
                    status=job.status,
                    result=job.result,
                    conversation_id=job.conversation_id,
                    idempotency_key=job.idempotency_key,
                    cancel_requested=False,
                )
            )
        return job

    async def get(self, job_id: UUID, user_id: UUID) -> JobRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(Query).where(Query.id == job_id, Query.user_id == user_id)
            )
            return self._record(row) if row else None

    async def find_idempotent(self, user_id: UUID, key: str) -> JobRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(Query).where(Query.user_id == user_id, Query.idempotency_key == key)
            )
            return self._record(row) if row else None

    async def update_status(
        self, job_id: UUID, status: QueryStatus, result: dict[str, Any] | None = None
    ) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                update(Query)
                .where(Query.id == job_id)
                .values(status=status, result=result, updated_at=datetime.now(UTC))
            )

    async def request_cancel(self, job_id: UUID, user_id: UUID) -> bool:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                update(Query)
                .where(Query.id == job_id, Query.user_id == user_id)
                .values(cancel_requested=True)
            )
            return bool(result.rowcount)

    async def reconcile_running(self) -> int:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                update(Query)
                .where(Query.status == QueryStatus.RUNNING)
                .values(status=QueryStatus.FAILED, result={"failure": "orphaned"})
            )
            return int(result.rowcount or 0)

    @staticmethod
    def _record(row: Query) -> JobRecord:
        return JobRecord(
            id=row.id,
            user_id=row.user_id,
            question=row.question,
            status=QueryStatus(row.status),
            result=row.result,
            conversation_id=row.conversation_id,
            idempotency_key=row.idempotency_key,
            cancel_requested=row.cancel_requested,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
