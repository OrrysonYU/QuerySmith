import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from querysmith.agent.runner import JobRunner
from querysmith.api.app import AppServices, create_app
from querysmith.auth.api_key import create_api_key
from querysmith.auth.rate_limit import TokenBucketLimiter
from querysmith.auth.service import AuthenticatedPrincipal, Authenticator
from querysmith.persistence.jobs import InMemoryJobRepository, JobRecord


@pytest.mark.asyncio
async def test_health_and_request_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-Id"].startswith("req_")
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_authenticated_async_job_flow_and_ownership() -> None:
    raw, record = create_api_key()
    user_id = uuid4()
    principal = AuthenticatedPrincipal(user_id=user_id, scopes=frozenset({"query"}))

    async def lookup(lookup_hash: str):
        return (record, principal) if lookup_hash == record.lookup_hash else None

    async def execute(job: JobRecord):
        await asyncio.sleep(0)
        return {"status": "SUCCEEDED", "answer": job.question}

    repository = InMemoryJobRepository()
    runner = JobRunner(repository, execute)
    services = AppServices(
        authenticator=Authenticator(lookup),
        limiter=TokenBucketLimiter(1000, 100),
        jobs=repository,
        runner=runner,
        readiness=lambda: asyncio.sleep(0, result={"status": "ready"}),
        events=lambda query_id, after: asyncio.sleep(0, result=[]),
        schema=lambda actor: asyncio.sleep(0, result={"tables": []}),
        sync_wait_seconds=0.2,
    )
    async with AsyncClient(
        transport=ASGITransport(app=create_app(services)), base_url="http://test"
    ) as client:
        unauthorized = await client.post("/api/v1/chat", json={"question": "x"})
        assert unauthorized.status_code == 401
        assert unauthorized.json()["error"]["code"] == "UNAUTHENTICATED"
        response = await client.post(
            "/api/v1/chat", headers={"X-API-Key": raw}, json={"question": "answer me"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "SUCCEEDED"
        status = await client.get(f"/api/v1/queries/{body['query_id']}", headers={"X-API-Key": raw})
        assert status.json()["result"]["answer"] == "answer me"
