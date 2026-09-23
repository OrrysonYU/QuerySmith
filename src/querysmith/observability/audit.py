"""Append-only audit service; no update or delete API is exposed."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.persistence.models import AuditLog


class AuditService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, *, actor_id: UUID | None, action: str, payload: dict[str, Any]) -> None:
        async with self._sessions() as session, session.begin():
            session.add(AuditLog(actor_id=actor_id, action=action, payload=payload))
