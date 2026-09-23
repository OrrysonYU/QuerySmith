"""Bounded LangGraph orchestration for the QuerySmith trust pipeline."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypedDict, cast

from langgraph.graph import END, StateGraph

from querysmith.agent.budgets import assert_budget
from querysmith.agent.error_taxonomy import ClassifiedFailure, FailureRoute, classify
from querysmith.agent.events import EventType, TraceEvent
from querysmith.agent.models import AnalysisResult, GenerationOutput, InterpretationOutcome
from querysmith.agent.repair import ensure_unique_attempt
from querysmith.agent.state import Budgets, Intent, QueryStatus, SqlAttempt
from querysmith.execution.executor import ExecutionLimits, ExecutionOutcome, QueryExecutor
from querysmith.observability.tracing import span
from querysmith.policy.config import SqlPolicy
from querysmith.policy.engine import authorize
from querysmith.schema_intel.retrieval import SchemaSubset
from querysmith.validation.semantic import SemanticStatus, SemanticVerdict
from querysmith.validation.shape import ShapeStatus, validate_shape
from querysmith.visualization.spec import ChartVerdict, validate_chart


class AgentServices(Protocol):
    async def interpret(self, question: str) -> InterpretationOutcome: ...
    async def select_schema(self, intent: Intent) -> SchemaSubset | None: ...
    async def generate(self, intent: Intent, schema: SchemaSubset) -> GenerationOutput: ...
    async def repair(
        self,
        intent: Intent,
        schema: SchemaSubset,
        attempts: list[SqlAttempt],
        failure: ClassifiedFailure,
    ) -> GenerationOutput: ...
    async def semantic_validate(
        self, intent: Intent, sql: str, result: ExecutionOutcome, schema: SchemaSubset
    ) -> SemanticVerdict: ...
    async def analyze(
        self, intent: Intent, result: ExecutionOutcome, assumptions: list[str]
    ) -> AnalysisResult: ...


class GraphState(TypedDict, total=False):
    question: str
    budgets: Budgets
    status: QueryStatus
    intent: Intent
    schema: SchemaSubset
    generation: GenerationOutput
    attempts: list[SqlAttempt]
    result: ExecutionOutcome
    analysis: AnalysisResult
    chart: ChartVerdict
    failure: ClassifiedFailure
    route: str
    events: list[TraceEvent]


def _event(state: GraphState, event_type: EventType, **safe_fields: Any) -> list[TraceEvent]:
    events = list(state.get("events", []))
    events.append(
        TraceEvent(sequence=len(events) + 1, event_type=event_type, safe_fields=safe_fields)
    )
    return events


def build_graph(
    *,
    services: AgentServices,
    policy: SqlPolicy,
    executor: QueryExecutor,
    limits: ExecutionLimits,
    dialect: str = "postgres",
) -> Any:
    def instrument(
        node_name: str,
        node: Callable[[GraphState], Awaitable[GraphState]],
    ) -> Callable[[GraphState], Awaitable[GraphState]]:
        async def wrapped(state: GraphState) -> GraphState:
            with span(f"agent.{node_name}", node=node_name):
                return await node(state)

        return wrapped

    async def interpret(state: GraphState) -> GraphState:
        assert_budget(state["budgets"], state.get("attempts", []))
        outcome = await services.interpret(state["question"])
        if outcome.refusal:
            return {
                "status": QueryStatus.BLOCKED,
                "route": "finalize",
                "events": _event(state, EventType.QUERY_BLOCKED, reason="question_refused"),
            }
        if outcome.ambiguity_flags:
            return {
                "status": QueryStatus.NEEDS_CLARIFICATION,
                "route": "finalize",
                "events": _event(
                    state,
                    EventType.QUESTION_INTERPRETED,
                    ambiguous=True,
                    questions=outcome.clarifying_questions,
                ),
            }
        intent = Intent(
            metric=outcome.metric,
            dimensions=outcome.dimensions,
            filters=outcome.filters,
            expected_columns=outcome.expected_columns,
            top_n=outcome.top_n,
            ambiguity_flags=[],
        )
        return {
            "intent": intent,
            "route": "continue",
            "events": _event(state, EventType.QUESTION_INTERPRETED),
        }

    async def select_schema(state: GraphState) -> GraphState:
        assert_budget(state["budgets"], state.get("attempts", []))
        subset = await services.select_schema(state["intent"])
        if subset is None or not subset.tables:
            return {
                "status": QueryStatus.NEEDS_CLARIFICATION,
                "route": "finalize",
                "events": _event(state, EventType.SCHEMA_SELECTED, tables=0),
            }
        return {
            "schema": subset,
            "route": "continue",
            "events": _event(state, EventType.SCHEMA_SELECTED, tables=len(subset.tables)),
        }

    async def generate(state: GraphState) -> GraphState:
        assert_budget(state["budgets"], state.get("attempts", []))
        generation = await services.generate(state["intent"], state["schema"])
        return {"generation": generation, "events": _event(state, EventType.SQL_GENERATED)}

    async def validate_sql(state: GraphState) -> GraphState:
        verdict = authorize(state["generation"].sql, policy, dialect)
        if not verdict.ok or not verdict.sql_hash or not verdict.rewritten_sql:
            failure = classify(policy_reason=verdict.reason)
            return {
                "failure": failure,
                "route": "failure",
                "events": _event(state, EventType.QUERY_FAILED, category=failure.category),
            }
        attempts = list(state.get("attempts", []))
        ensure_unique_attempt(verdict.sql_hash, attempts, state["budgets"].max_attempts)
        attempts.append(SqlAttempt(sql=verdict.rewritten_sql, sql_hash=verdict.sql_hash))
        generation = state["generation"].model_copy(update={"sql": verdict.rewritten_sql})
        return {
            "generation": generation,
            "attempts": attempts,
            "route": "execute",
            "events": _event(state, EventType.SQL_VALIDATED),
        }

    async def execute(state: GraphState) -> GraphState:
        result = await executor.execute(state["generation"].sql, limits)
        if result.error:
            failure = classify(database_error=result.error.category)
            return {
                "result": result,
                "failure": failure,
                "route": "failure",
                "events": _event(state, EventType.QUERY_FAILED, category=failure.category),
            }
        return {
            "result": result,
            "route": "shape",
            "events": _event(
                state,
                EventType.QUERY_EXECUTED,
                rows=result.row_count,
                duration_ms=result.duration_ms,
            ),
        }

    async def shape(state: GraphState) -> GraphState:
        verdict = validate_shape(state["result"], state["intent"])
        if verdict.status in {ShapeStatus.MISMATCH, ShapeStatus.EMPTY}:
            failure = classify(semantic_mismatch=True)
            failure = failure.model_copy(update={"category": f"shape_{verdict.status.lower()}"})
            return {
                "failure": failure,
                "route": "failure",
                "events": _event(state, EventType.QUERY_FAILED, category=failure.category),
            }
        return {
            "route": "semantic",
            "events": _event(
                state, EventType.RESULT_VALIDATED, stage="shape", verdict=verdict.status
            ),
        }

    async def semantic(state: GraphState) -> GraphState:
        verdict = await services.semantic_validate(
            state["intent"], state["generation"].sql, state["result"], state["schema"]
        )
        if verdict.status is SemanticStatus.MISMATCH:
            failure = classify(semantic_mismatch=True)
            attempts = list(state["attempts"])
            attempts[-1] = attempts[-1].model_copy(update={"critique": verdict.critique})
            return {
                "attempts": attempts,
                "failure": failure,
                "route": "failure",
                "events": _event(state, EventType.QUERY_FAILED, category="semantic"),
            }
        if verdict.status is SemanticStatus.INSUFFICIENT_DATA:
            return {
                "status": QueryStatus.NEEDS_CLARIFICATION,
                "route": "finalize",
                "events": _event(state, EventType.RESULT_VALIDATED, verdict=verdict.status),
            }
        return {
            "route": "analyze",
            "events": _event(
                state, EventType.RESULT_VALIDATED, stage="semantic", verdict=verdict.status
            ),
        }

    async def handle_failure(state: GraphState) -> GraphState:
        failure = state["failure"]
        if failure.route is FailureRoute.BLOCK:
            return {
                "status": QueryStatus.BLOCKED,
                "route": "finalize",
                "events": _event(state, EventType.QUERY_BLOCKED, reason=failure.category),
            }
        if (
            failure.route is not FailureRoute.REPAIR
            or len(state.get("attempts", [])) >= state["budgets"].max_attempts
        ):
            return {"status": QueryStatus.FAILED, "route": "finalize"}
        if failure.category == "timeout" and state["budgets"].resource_repairs >= 1:
            return {"status": QueryStatus.FAILED, "route": "finalize"}
        if (
            failure.category.startswith(("semantic", "shape"))
            and state["budgets"].semantic_repairs >= 1
        ):
            return {"status": QueryStatus.NEEDS_CLARIFICATION, "route": "finalize"}
        budgets = state["budgets"].model_copy(deep=True)
        if failure.category == "timeout":
            budgets.resource_repairs += 1
        if failure.category.startswith(("semantic", "shape")):
            budgets.semantic_repairs += 1
        return {"budgets": budgets, "route": "repair"}

    async def repair(state: GraphState) -> GraphState:
        generation = await services.repair(
            state["intent"], state["schema"], state.get("attempts", []), state["failure"]
        )
        return {
            "generation": generation,
            "route": "validate",
            "events": _event(
                state, EventType.SQL_REPAIRED, attempt=len(state.get("attempts", [])) + 1
            ),
        }

    async def analyze(state: GraphState) -> GraphState:
        analysis = await services.analyze(
            state["intent"], state["result"], state["generation"].assumptions
        )
        return {
            "analysis": analysis,
            "route": "render",
            "events": _event(state, EventType.ANALYSIS_COMPLETED),
        }

    async def render(state: GraphState) -> GraphState:
        if state["analysis"].chart_spec is None:
            return {"route": "finalize"}
        return {
            "chart": validate_chart(state["analysis"].chart_spec, state["result"]),
            "route": "finalize",
        }

    async def finalize(state: GraphState) -> GraphState:
        status = state.get("status")
        if status is None or status is QueryStatus.RUNNING:
            status = QueryStatus.SUCCEEDED if "analysis" in state else QueryStatus.FAILED
        return {"status": status, "events": _event(state, EventType.QUERY_COMPLETED, status=status)}

    graph = StateGraph(GraphState)
    for name, node in (
        ("interpret", interpret),
        ("select_schema", select_schema),
        ("generate", generate),
        ("validate_sql", validate_sql),
        ("execute", execute),
        ("shape", shape),
        ("semantic", semantic),
        ("handle_failure", handle_failure),
        ("repair", repair),
        ("analyze", analyze),
        ("render", render),
        ("finalize", finalize),
    ):
        graph.add_node(name, cast(Any, instrument(name, node)))
    graph.set_entry_point("interpret")
    graph.add_conditional_edges(
        "interpret", lambda s: s["route"], {"continue": "select_schema", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "select_schema", lambda s: s["route"], {"continue": "generate", "finalize": "finalize"}
    )
    graph.add_edge("generate", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql", lambda s: s["route"], {"execute": "execute", "failure": "handle_failure"}
    )
    graph.add_conditional_edges(
        "execute", lambda s: s["route"], {"shape": "shape", "failure": "handle_failure"}
    )
    graph.add_conditional_edges(
        "shape", lambda s: s["route"], {"semantic": "semantic", "failure": "handle_failure"}
    )
    graph.add_conditional_edges(
        "semantic",
        lambda s: s["route"],
        {"analyze": "analyze", "failure": "handle_failure", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "handle_failure", lambda s: s["route"], {"repair": "repair", "finalize": "finalize"}
    )
    graph.add_edge("repair", "validate_sql")
    graph.add_edge("analyze", "render")
    graph.add_edge("render", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_query(graph: Any, *, question: str, budgets: Budgets) -> GraphState:
    initial: GraphState = {
        "question": question,
        "budgets": budgets,
        "status": QueryStatus.RUNNING,
        "attempts": [],
        "events": [],
    }
    try:
        return cast(GraphState, await graph.ainvoke(initial))
    except TimeoutError:
        return {
            **initial,
            "status": QueryStatus.CANCELLED,
            "events": _event(initial, EventType.QUERY_COMPLETED, status=QueryStatus.CANCELLED),
        }
    except Exception:
        return {
            **initial,
            "status": QueryStatus.FAILED,
            "events": _event(initial, EventType.QUERY_COMPLETED, status=QueryStatus.FAILED),
        }
