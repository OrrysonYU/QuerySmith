"""Versioned FastAPI application and complete Level-1 query API."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from querysmith.agent.runner import JobRunner
from querysmith.agent.state import QueryStatus
from querysmith.api.schemas import ChatRequest, ChatResponse
from querysmith.auth.rate_limit import TokenBucketLimiter
from querysmith.auth.service import AuthenticatedPrincipal, Authenticator
from querysmith.core.errors import QuerySmithError
from querysmith.core.ids import new_id
from querysmith.observability.metrics import RATE_LIMITED, REQUEST_SECONDS, REQUESTS
from querysmith.persistence.jobs import JobRecord, JobRepository


@dataclass
class AppServices:
    authenticator: Authenticator
    limiter: TokenBucketLimiter
    jobs: JobRepository
    runner: JobRunner
    readiness: Callable[[], Awaitable[dict[str, Any]]]
    events: Callable[[UUID, int], Awaitable[list[dict[str, object]]]]
    schema: Callable[[AuthenticatedPrincipal], Awaitable[dict[str, Any]]]
    sync_wait_seconds: float = 25
    startup: Callable[[], Awaitable[None]] | None = None
    shutdown: Callable[[], Awaitable[None]] | None = None


def create_app(services: AppServices | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if services and services.startup:
            await services.startup()
        try:
            yield
        finally:
            if services and services.shutdown:
                await services.shutdown()

    app = FastAPI(
        title="QuerySmith",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Any]]
    ) -> Any:
        request_id = request.headers.get("X-Request-Id") or new_id("req")
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        route = request.url.path
        REQUESTS.labels(route=route, status=str(response.status_code)).inc()
        REQUEST_SECONDS.labels(route=route).observe(time.perf_counter() - started)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(QuerySmithError)
    async def querysmith_error(request: Request, exc: QuerySmithError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.safe_message,
                    "request_id": request.state.request_id,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            401: "UNAUTHENTICATED",
            404: "NOT_FOUND",
            429: "RATE_LIMITED",
            503: "DATASOURCE_UNAVAILABLE",
        }
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": codes.get(exc.status_code, "QUERY_FAILED"),
                    "message": str(exc.detail),
                    "request_id": request.state.request_id,
                    "details": {},
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(error["loc"]), "type": error["type"]} for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "QUESTION_INVALID",
                    "message": "Request validation failed.",
                    "request_id": request.state.request_id,
                    "details": {"fields": details},
                }
            },
        )

    async def principal(x_api_key: str | None = Header(default=None)) -> AuthenticatedPrincipal:
        if services is None or not x_api_key:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        actor = await services.authenticator.authenticate(x_api_key)
        if actor is None:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        if not await services.limiter.allow(str(actor.user_id)):
            RATE_LIMITED.inc()
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"}
            )
        return actor

    def configured() -> AppServices:
        if services is None:
            raise HTTPException(status_code=503, detail="Service is not configured")
        return services

    Principal = Annotated[AuthenticatedPrincipal, Depends(principal)]

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/readiness")
    async def ready() -> dict[str, Any]:
        if services is None:
            return {"status": "not_ready", "checks": {"configuration": "missing"}}
        return await services.readiness()

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/v1/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, actor: Principal) -> ChatResponse:
        configured_services = configured()
        job = await configured_services.runner.submit(
            JobRecord(
                user_id=actor.user_id,
                question=payload.question,
                conversation_id=payload.conversation_id,
                idempotency_key=payload.idempotency_key,
            )
        )
        if payload.mode == "auto":
            deadline = asyncio.get_running_loop().time() + configured_services.sync_wait_seconds
            while asyncio.get_running_loop().time() < deadline:
                current = await configured_services.jobs.get(job.id, actor.user_id)
                if current and current.status not in {QueryStatus.QUEUED, QueryStatus.RUNNING}:
                    return ChatResponse(
                        query_id=str(job.id), status=current.status, result=current.result
                    )
                await asyncio.sleep(0.02)
        return ChatResponse(query_id=str(job.id), status=job.status)

    @app.get("/api/v1/queries/{query_id}", response_model=ChatResponse)
    async def get_query(query_id: UUID, actor: Principal) -> ChatResponse:
        job = await configured().jobs.get(query_id, actor.user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Not found")
        return ChatResponse(query_id=str(job.id), status=job.status, result=job.result)

    @app.get("/api/v1/queries/{query_id}/events")
    async def get_events(
        query_id: UUID,
        actor: Principal,
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        configured_services = configured()
        job = await configured_services.jobs.get(query_id, actor.user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Not found")
        events = await configured_services.events(query_id, after)
        return {
            "query_id": str(query_id),
            "events": events,
            "next_cursor": events[-1]["sequence"] if events else after,
        }

    @app.post("/api/v1/queries/{query_id}/cancel")
    async def cancel(query_id: UUID, actor: Principal) -> dict[str, str]:
        if not await configured().runner.cancel(query_id, actor.user_id):
            raise HTTPException(status_code=404, detail="Not found")
        return {"query_id": str(query_id), "status": "CANCELLING"}

    @app.get("/api/v1/queries/{query_id}/chart")
    async def chart(query_id: UUID, actor: Principal) -> FileResponse:
        job = await configured().jobs.get(query_id, actor.user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Not found")
        artifact = Path("_charts") / str(query_id) / "chart.html"
        if not artifact.is_file():
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(
            artifact,
            media_type="text/html",
            headers={
                "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'"
            },
        )

    @app.get("/api/v1/schema")
    async def schema(actor: Principal) -> dict[str, Any]:
        return await configured().schema(actor)

    return app


app = create_app()
