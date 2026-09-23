"""Append-only SQL attempt persistence."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.agent.state import SqlAttempt
from querysmith.persistence.models import QueryAttempt


class AttemptStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def append_all(self, query_id: UUID, attempts: list[SqlAttempt]) -> None:
        async with self._sessions() as session, session.begin():
            for index, attempt in enumerate(attempts, start=1):
                session.add(
                    QueryAttempt(
                        query_id=query_id,
                        sequence=index,
                        sql=attempt.sql,
                        payload=attempt.model_dump(mode="json"),
                    )
                )
