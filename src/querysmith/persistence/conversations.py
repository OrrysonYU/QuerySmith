"""Permission-scoped conversation summary access."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.persistence.models import Conversation


class ConversationRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def summary(self, conversation_id: UUID | None, user_id: UUID) -> str | None:
        if conversation_id is None:
            return None
        async with self._sessions() as session:
            value = await session.scalar(
                select(Conversation.summary).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            return value
