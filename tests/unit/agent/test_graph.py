from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import pytest

from querysmith.agent.error_taxonomy import ClassifiedFailure
from querysmith.agent.graph import build_graph, run_query
from querysmith.agent.models import AnalysisResult, GenerationOutput, InterpretationOutcome
from querysmith.agent.state import Budgets, Intent, QueryStatus, SqlAttempt
from querysmith.execution.executor import ExecutionLimits, QueryExecutor
from querysmith.policy.config import SqlPolicy
from querysmith.schema_intel.models import ColumnInfo, TableInfo
from querysmith.schema_intel.retrieval import SchemaSubset
from querysmith.validation.semantic import SemanticStatus, SemanticVerdict


class Stream:
    columns: ClassVar[list[str]] = ["total"]

    def __init__(self, rows: list[list[Any]]) -> None:
        self.rows = rows

    def __aiter__(self) -> "Stream":
        self._iterator = iter(self.rows)
        return self

    async def __anext__(self) -> list[Any]:
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class Services:
    repair_calls = 0
    sql = "SELECT SUM(customer.amount) AS total FROM customer"

    async def interpret(self, question: str) -> InterpretationOutcome:
        del question
        return InterpretationOutcome(metric="total", expected_columns=["total"])

    async def select_schema(self, intent: Intent) -> SchemaSubset | None:
        del intent
        return SchemaSubset(
            tables=[
                TableInfo(name="customer", columns=[ColumnInfo(name="amount", data_type="number")])
            ],
            relationships=[],
        )

    async def generate(self, intent: Intent, schema: SchemaSubset) -> GenerationOutput:
        del intent, schema
        return GenerationOutput(sql=self.sql, expected_columns=["total"])

    async def repair(
        self,
        intent: Intent,
        schema: SchemaSubset,
        attempts: list[SqlAttempt],
        failure: ClassifiedFailure,
    ) -> GenerationOutput:
        del intent, schema, attempts, failure
        self.repair_calls += 1
        return GenerationOutput(
            sql="SELECT SUM(customer.amount) AS total FROM customer", expected_columns=["total"]
        )

    async def semantic_validate(
        self, intent: Intent, sql: str, result: Any, schema: SchemaSubset
    ) -> SemanticVerdict:
        del intent, sql, result, schema
        return SemanticVerdict(status=SemanticStatus.MATCH)

    async def analyze(self, intent: Intent, result: Any, assumptions: list[str]) -> AnalysisResult:
        del intent, result, assumptions
        return AnalysisResult(answer_markdown="Total is 42")


def budgets() -> Budgets:
    return Budgets.with_deadline(datetime.now(UTC) + timedelta(seconds=10))


@pytest.mark.asyncio
async def test_graph_happy_path_reaches_success() -> None:
    services = Services()
    graph = build_graph(
        services=services,
        policy=SqlPolicy(allowed_tables=frozenset({"customer"})),
        executor=QueryExecutor(lambda sql: Stream([[42]])),
        limits=ExecutionLimits(),
    )
    state = await run_query(graph, question="total?", budgets=budgets())
    assert state["status"] is QueryStatus.SUCCEEDED
    assert state["analysis"].answer_markdown == "Total is 42"
    assert len(state["attempts"]) == 1


@pytest.mark.asyncio
async def test_security_block_is_terminal_without_repair() -> None:
    services = Services()
    services.sql = "SELECT secret.value FROM secret"
    graph = build_graph(
        services=services,
        policy=SqlPolicy(allowed_tables=frozenset({"customer"})),
        executor=QueryExecutor(lambda sql: Stream([[42]])),
        limits=ExecutionLimits(),
    )
    state = await run_query(graph, question="steal", budgets=budgets())
    assert state["status"] is QueryStatus.BLOCKED
    assert services.repair_calls == 0
