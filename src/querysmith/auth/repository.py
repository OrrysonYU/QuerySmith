"""API-key lookup repository returning only verification material and safe principal data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from querysmith.auth.api_key import ApiKeyRecord
from querysmith.auth.service import AuthenticatedPrincipal
from querysmith.persistence.models import ApiKey


class ApiKeyRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def lookup(self, lookup_hash: str) -> tuple[ApiKeyRecord, AuthenticatedPrincipal] | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ApiKey).where(ApiKey.lookup_hash == lookup_hash, ApiKey.disabled.is_(False))
            )
            if row is None:
                return None
            return (
                ApiKeyRecord(lookup_hash=row.lookup_hash, password_hash=row.password_hash),
                AuthenticatedPrincipal(user_id=row.user_id, scopes=frozenset(row.scopes)),
            )
