"""API-key authentication independent of transport and persistence implementation."""

import hashlib
from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import BaseModel

from querysmith.auth.api_key import ApiKeyRecord, verify_api_key


class AuthenticatedPrincipal(BaseModel):
    user_id: UUID
    scopes: frozenset[str]
    rate_limit_per_minute: int = 20


LookupApiKey = Callable[[str], Awaitable[tuple[ApiKeyRecord, AuthenticatedPrincipal] | None]]


class Authenticator:
    def __init__(self, lookup: LookupApiKey) -> None:
        self._lookup = lookup

    async def authenticate(self, raw_key: str) -> AuthenticatedPrincipal | None:
        lookup_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        found = await self._lookup(lookup_hash)
        if found is None:
            return None
        record, principal = found
        return principal if verify_api_key(raw_key, record) else None
