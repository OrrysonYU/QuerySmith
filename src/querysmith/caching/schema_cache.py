"""Version-aware in-process schema cache with explicit invalidation."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from querysmith.schema_intel.models import SchemaSnapshot


@dataclass(frozen=True)
class CacheEntry:
    snapshot: SchemaSnapshot
    expires_at: float


class SchemaCache:
    def __init__(self, ttl_seconds: float = 300) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self.hits = 0
        self.misses = 0

    async def get(
        self, source: str, loader: Callable[[], Awaitable[SchemaSnapshot]]
    ) -> SchemaSnapshot:
        now = time.monotonic()
        entry = self._entries.get(source)
        if entry and entry.expires_at > now:
            self.hits += 1
            return entry.snapshot
        lock = self._locks.setdefault(source, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            entry = self._entries.get(source)
            if entry and entry.expires_at > now:
                self.hits += 1
                return entry.snapshot
            self.misses += 1
            snapshot = await loader()
            self._entries[source] = CacheEntry(snapshot, now + self._ttl)
            return snapshot

    def invalidate(self, source: str) -> None:
        self._entries.pop(source, None)
