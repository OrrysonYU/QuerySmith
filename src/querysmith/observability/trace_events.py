"""Append-only safe trace-event persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.agent.events import TraceEvent as AgentTraceEvent
from querysmith.persistence.models import TraceEvent


class TraceEventStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def append(self, query_id: UUID, event: AgentTraceEvent) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                TraceEvent(
                    query_id=query_id,
                    sequence=event.sequence,
                    event_type=event.event_type,
                    payload=event.model_dump(mode="json"),
                )
            )

    async def list_after(
        self, query_id: UUID, cursor: int, limit: int = 100
    ) -> list[dict[str, object]]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(TraceEvent)
                    .where(TraceEvent.query_id == query_id, TraceEvent.sequence > cursor)
                    .order_by(TraceEvent.sequence)
                    .limit(limit)
                )
            ).all()
            return [
                {"sequence": row.sequence, "event_type": row.event_type, "payload": row.payload}
                for row in rows
            ]
