import pytest

from querysmith.auth.api_key import create_api_key, verify_api_key
from querysmith.auth.rate_limit import TokenBucketLimiter


def test_api_key_is_hashed_and_verifies() -> None:
    raw, record = create_api_key()
    assert raw not in record.password_hash and verify_api_key(raw, record)
    assert not verify_api_key(raw + "x", record)


@pytest.mark.asyncio
async def test_rate_limit_bounds_burst() -> None:
    limiter = TokenBucketLimiter(rate_per_minute=1, burst=1)
    assert await limiter.allow("key")
    assert not await limiter.allow("key")
