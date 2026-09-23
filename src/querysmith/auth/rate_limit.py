"""Concurrency-safe in-process token bucket."""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketLimiter:
    def __init__(self, rate_per_minute: int, burst: int) -> None:
        self._rate = rate_per_minute / 60
        self._burst = burst
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.setdefault(key, _Bucket(float(self._burst), now))
            bucket.tokens = min(self._burst, bucket.tokens + (now - bucket.updated_at) * self._rate)
            bucket.updated_at = now
            if bucket.tokens < 1:
                return False
            bucket.tokens -= 1
            return True
