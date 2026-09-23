import asyncio

import pytest

from querysmith.caching.schema_cache import SchemaCache
from querysmith.schema_intel.models import SchemaSnapshot


@pytest.mark.asyncio
async def test_schema_cache_ttl_and_invalidation() -> None:
    calls = 0

    async def loader() -> SchemaSnapshot:
        nonlocal calls
        calls += 1
        return SchemaSnapshot(source="x", tables=[], signature=str(calls))

    cache = SchemaCache(ttl_seconds=60)
    assert (await cache.get("x", loader)).signature == "1"
    assert (await cache.get("x", loader)).signature == "1"
    assert cache.hits == 1 and cache.misses == 1
    cache.invalidate("x")
    assert (await cache.get("x", loader)).signature == "2"
    await asyncio.sleep(0)
