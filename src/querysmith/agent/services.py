"""Production agent services backed by typed LLM calls and permission-filtered schema retrieval."""

from collections.abc import Awaitable, Callable

from querysmith.agent.error_taxonomy import ClassifiedFailure
from querysmith.agent.models import (
    AnalysisResult,
    GenerationOutput,
    InterpretationOutcome,
    SchemaSelection,
)
from querysmith.agent.state import Intent, SqlAttempt
from querysmith.execution.executor import ExecutionOutcome
from querysmith.llm.client import LLMCallContext, LLMClient, PromptRef
from querysmith.schema_intel.models import SchemaSnapshot
from querysmith.schema_intel.retrieval import SchemaSubset, select_candidates
from querysmith.validation.semantic import SemanticVerdict


class LLMAgentServices:
    def __init__(
        self,
        *,
        llm: LLMClient,
        context: LLMCallContext,
        load_schema: Callable[[], Awaitable[SchemaSnapshot]],
        allowed_tables: frozenset[str],
        blocked_columns: frozenset[str] = frozenset(),
        conversation_summary: str | None = None,
    ) -> None:
        self._llm = llm
        self._context = context
        self._load_schema = load_schema
        self._allowed_tables = allowed_tables
        self._blocked_columns = blocked_columns
        self._conversation_summary = conversation_summary

    async def interpret(self, question: str) -> InterpretationOutcome:
        return await self._llm.complete_structured(
            prompt=PromptRef("interpret_question", 1),
            variables={
                "question": question,
                "conversation_summary": self._conversation_summary or "",
            },
            response_model=InterpretationOutcome,
            context=self._context,
        )

    async def select_schema(self, intent: Intent) -> SchemaSubset | None:
        snapshot = await self._load_schema()
        query = " ".join([intent.metric, *intent.dimensions, *intent.filters])
        subset = select_candidates(
            snapshot,
            query,
            self._allowed_tables,
            self._blocked_columns,
            max_tables=8,
        )
        if not subset.tables:
            return None
        selection = await self._llm.complete_structured(
            prompt=PromptRef("select_schema", 1),
            variables={
                "intent": intent.model_dump_json(),
                "candidates": subset.model_dump_json(),
            },
            response_model=SchemaSelection,
            context=self._context,
        )
        selected_names = {name.lower() for name in selection.table_names}
        tables = [
            table
            for table in subset.tables
            if table.name.lower() in selected_names
            or table.qualified_name.lower() in selected_names
        ]
        if not tables:
            return None
        retained = {table.name for table in tables} | {table.qualified_name for table in tables}
        relationships = [
            relationship
            for relationship in subset.relationships
            if relationship.source_table in retained and relationship.target_table in retained
        ]
        return SchemaSubset(tables=tables, relationships=relationships)

    async def generate(self, intent: Intent, schema: SchemaSubset) -> GenerationOutput:
        return await self._llm.complete_structured(
            prompt=PromptRef("generate_sql", 1),
            variables={
                "intent": intent.model_dump_json(),
                "schema": schema.model_dump_json(),
            },
            response_model=GenerationOutput,
            context=self._context,
        )

    async def repair(
        self,
        intent: Intent,
        schema: SchemaSubset,
        attempts: list[SqlAttempt],
        failure: ClassifiedFailure,
    ) -> GenerationOutput:
        return await self._llm.complete_structured(
            prompt=PromptRef("repair_sql", 1),
            variables={
                "intent": intent.model_dump_json(),
                "schema": schema.model_dump_json(),
                "attempts": [attempt.model_dump(mode="json") for attempt in attempts],
                "failure": failure.model_dump_json(),
            },
            response_model=GenerationOutput,
            context=self._context,
        )

    async def semantic_validate(
        self,
        intent: Intent,
        sql: str,
        result: ExecutionOutcome,
        schema: SchemaSubset,
    ) -> SemanticVerdict:
        return await self._llm.complete_structured(
            prompt=PromptRef("validate_result", 1),
            variables={
                "intent": intent.model_dump_json(),
                "sql": sql,
                "rows": result.rows[:50],
                "schema": schema.model_dump_json(),
            },
            response_model=SemanticVerdict,
            context=self._context,
        )

    async def analyze(
        self,
        intent: Intent,
        result: ExecutionOutcome,
        assumptions: list[str],
    ) -> AnalysisResult:
        analysis = await self._llm.complete_structured(
            prompt=PromptRef("analyze_result", 1),
            variables={
                "intent": intent.model_dump_json(),
                "rows": result.rows,
                "columns": result.columns,
                "assumptions": assumptions,
            },
            response_model=AnalysisResult,
            context=self._context,
        )
        merged = list(dict.fromkeys([*assumptions, *analysis.caveats]))
        return analysis.model_copy(update={"caveats": merged})
