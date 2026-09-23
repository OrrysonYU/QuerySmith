"""Production dependency wiring without import-time network access."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from querysmith.agent.graph import build_graph, run_query
from querysmith.agent.runner import JobRunner
from querysmith.agent.services import LLMAgentServices
from querysmith.agent.state import Budgets
from querysmith.api.app import AppServices
from querysmith.auth.rate_limit import TokenBucketLimiter
from querysmith.auth.repository import ApiKeyRepository
from querysmith.auth.service import AuthenticatedPrincipal, Authenticator
from querysmith.core.config import Settings, get_settings
from querysmith.execution.connection_manager import ConnectionManager
from querysmith.execution.datasource import DataSourceConfig, DataSourceRegistry, Dialect
from querysmith.execution.executor import ExecutionLimits, QueryExecutor
from querysmith.execution.postgres import postgres_stream_factory
from querysmith.llm.adapters.mock import MockLLMClient
from querysmith.llm.client import LLMCallContext
from querysmith.llm.factory import build_llm_client
from querysmith.llm.prompts.registry import PromptRegistry
from querysmith.observability.audit import AuditService
from querysmith.observability.metrics import (
    AUDIT_FAILURES,
    DB_ROWS,
    DB_SECONDS,
    LLM_TOKENS,
    QUERIES,
    QUERY_ATTEMPTS,
)
from querysmith.observability.trace_events import TraceEventStore
from querysmith.observability.tracing import configure_tracing
from querysmith.persistence.attempts import AttemptStore
from querysmith.persistence.conversations import ConversationRepository
from querysmith.persistence.jobs import JobRecord, SqlJobRepository
from querysmith.persistence.session import create_engine, create_session_factory
from querysmith.policy.config import SqlPolicy
from querysmith.schema_intel.introspection import introspect_postgres
from querysmith.schema_intel.models import SchemaSnapshot
from querysmith.visualization.renderer import render_chart
from querysmith.visualization.spec import ChartType


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        configure_tracing(endpoint=settings.observability.otlp_endpoint)
        self.engine = create_engine(settings.datasource.app_database_url.get_secret_value())
        self.sessions = create_session_factory(self.engine)
        source_url = settings.datasource.source_database_url
        self.source_configured = source_url is not None
        registry = DataSourceRegistry(
            [
                DataSourceConfig(
                    name=settings.datasource.default_source,
                    dialect=Dialect.POSTGRES,
                    secret_reference="runtime:source_database_url",
                    statement_timeout_ms=settings.datasource.statement_timeout_ms,
                )
            ]
        )
        self.connections = ConnectionManager(
            registry,
            secret_resolver=lambda reference: self._source_secret(reference),
        )
        prompts = PromptRegistry(Path("prompts"))
        self.llm = (
            MockLLMClient({})
            if settings.llm.provider == "mock"
            else build_llm_client(settings.llm, prompts)
        )
        self.allowed_tables = frozenset(
            value.strip()
            for value in settings.datasource.allowed_tables_csv.split(",")
            if value.strip()
        )
        self.blocked_columns = frozenset(
            value.strip()
            for value in settings.datasource.blocked_columns_csv.split(",")
            if value.strip()
        )
        self.jobs = SqlJobRepository(self.sessions)
        self.audit = AuditService(self.sessions)
        self.events = TraceEventStore(self.sessions)
        self.attempts = AttemptStore(self.sessions)
        self.conversations = ConversationRepository(self.sessions)
        self.runner = JobRunner(
            self.jobs,
            self.execute_job,
            max_concurrency=settings.core.max_concurrent_jobs,
        )
        key_repository = ApiKeyRepository(self.sessions)
        self.services = AppServices(
            authenticator=Authenticator(key_repository.lookup),
            limiter=TokenBucketLimiter(20, 20),
            jobs=self.jobs,
            runner=self.runner,
            readiness=self.readiness,
            events=self.events.list_after,
            schema=self.schema_for,
            sync_wait_seconds=settings.core.sync_wait_seconds,
            startup=self.startup,
            shutdown=self.shutdown,
        )

    def _source_secret(self, reference: str) -> SecretStr:
        del reference
        if self.settings.datasource.source_database_url is None:
            raise ValueError("QS_DATASOURCE__SOURCE_DATABASE_URL is required")
        return self.settings.datasource.source_database_url

    async def startup(self) -> None:
        if self.source_configured:
            await self.connections.start()
        await self.runner.start()

    async def shutdown(self) -> None:
        await self.runner.shutdown()
        await self.connections.close_all()
        close = getattr(self.llm, "close", None)
        if close is not None:
            await close()
        await self.engine.dispose()

    async def readiness(self) -> dict[str, Any]:
        app_db = False
        try:
            async with self.engine.connect() as connection:
                await connection.exec_driver_sql("SELECT 1")
            app_db = True
        except Exception:
            app_db = False
        source = (
            await self.connections.healthcheck(self.settings.datasource.default_source)
            if self.source_configured
            else False
        )
        llm = self.settings.llm.provider != "mock" and self.settings.llm.api_key is not None
        ready = app_db and source and llm
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {"app_database": app_db, "data_source": source, "llm": llm},
        }

    async def schema_for(self, actor: AuthenticatedPrincipal) -> dict[str, Any]:
        del actor
        if not self.source_configured:
            return {"tables": []}
        async with self.connections.acquire(self.settings.datasource.default_source) as connection:
            snapshot = await introspect_postgres(
                connection, self.settings.datasource.default_source
            )
        tables = [
            {
                "name": table.qualified_name,
                "columns": [
                    column.name
                    for column in table.columns
                    if f"{table.name}.{column.name}" not in self.blocked_columns
                ],
            }
            for table in snapshot.tables
            if table.name in self.allowed_tables or table.qualified_name in self.allowed_tables
        ]
        return {"schema_version": snapshot.signature, "tables": tables}

    async def execute_job(self, job: JobRecord) -> dict[str, Any]:
        try:
            await self.audit.record(
                actor_id=job.user_id, action="query.started", payload={"query_id": str(job.id)}
            )
        except Exception:
            AUDIT_FAILURES.inc()

        async def load_schema() -> SchemaSnapshot:
            async with self.connections.acquire(
                self.settings.datasource.default_source
            ) as connection:
                return await introspect_postgres(
                    connection, self.settings.datasource.default_source
                )

        context = LLMCallContext(
            remaining_calls=self.settings.llm.max_calls_per_query,
            remaining_tokens=self.settings.llm.max_tokens_per_query,
        )
        services = LLMAgentServices(
            llm=self.llm,
            context=context,
            load_schema=load_schema,
            allowed_tables=self.allowed_tables,
            blocked_columns=self.blocked_columns,
            conversation_summary=await self.conversations.summary(job.conversation_id, job.user_id),
        )
        policy = SqlPolicy(
            allowed_tables=self.allowed_tables,
            blocked_columns=self.blocked_columns,
            max_rows=self.settings.policy.max_rows,
            require_limit=self.settings.policy.require_limit,
            reject_select_star=self.settings.policy.reject_select_star,
        )
        executor = QueryExecutor(
            postgres_stream_factory(self.connections, self.settings.datasource.default_source)
        )
        graph = build_graph(
            services=services,
            policy=policy,
            executor=executor,
            limits=ExecutionLimits(
                timeout_seconds=self.settings.datasource.statement_timeout_ms / 1000,
                max_rows=self.settings.datasource.max_rows,
                max_bytes=self.settings.datasource.max_bytes,
            ),
        )
        state = await run_query(
            graph,
            question=job.question,
            budgets=Budgets.with_deadline(
                datetime.now(UTC) + timedelta(seconds=self.settings.core.request_deadline_seconds)
            ),
        )
        for event in state.get("events", []):
            await self.events.append(job.id, event)
        await self.attempts.append_all(job.id, state.get("attempts", []))
        analysis = state.get("analysis")
        generation = state.get("generation")
        execution_result = state.get("result")
        chart = state.get("chart")
        rendered_ref: str | None = None
        if (
            chart
            and chart.valid
            and chart.spec
            and chart.spec.chart_type is not ChartType.TABLE
            and execution_result
        ):
            artifact = Path("_charts") / str(job.id) / "chart.html"
            try:
                render_chart(chart.spec, execution_result, artifact)
                rendered_ref = f"/api/v1/queries/{job.id}/chart"
            except Exception:
                rendered_ref = None
        result = {
            "status": state["status"],
            "analysis": analysis.model_dump(mode="json") if analysis else None,
            "sql": generation.sql if generation else None,
            "attempts": len(state.get("attempts", [])),
            "result": execution_result.model_dump(mode="json") if execution_result else None,
            "chart": (
                {
                    "spec": chart.spec.model_dump(mode="json") if chart and chart.spec else None,
                    "rendered_ref": rendered_ref,
                    "warning": chart.warning if chart else None,
                }
                if chart
                else None
            ),
            "token_usage": {
                "prompt": context.prompt_tokens,
                "completion": context.completion_tokens,
            },
        }
        QUERIES.labels(status=str(state["status"])).inc()
        QUERY_ATTEMPTS.observe(len(state.get("attempts", [])))
        LLM_TOKENS.labels(type="prompt").inc(context.prompt_tokens)
        LLM_TOKENS.labels(type="completion").inc(context.completion_tokens)
        if execution_result:
            DB_SECONDS.labels(datasource=self.settings.datasource.default_source).observe(
                execution_result.duration_ms / 1000
            )
            DB_ROWS.observe(execution_result.row_count)
        try:
            await self.audit.record(
                actor_id=job.user_id,
                action="query.completed",
                payload={"query_id": str(job.id), "status": str(state["status"])},
            )
        except Exception:
            AUDIT_FAILURES.inc()
        return result


def build_runtime() -> Runtime:
    return Runtime(get_settings())
