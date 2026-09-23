"""Structured probabilistic-boundary models."""

from pydantic import BaseModel, Field

from querysmith.visualization.spec import ChartSpec


class InterpretationOutcome(BaseModel):
    metric: str
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    top_n: int | None = None
    ambiguity_flags: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    refusal: bool = False


class GenerationOutput(BaseModel):
    sql: str = Field(min_length=1)
    expected_columns: list[str] = Field(min_length=1)
    aggregation_notes: str = ""
    assumptions: list[str] = Field(default_factory=list)


class SchemaSelection(BaseModel):
    table_names: list[str] = Field(min_length=1, max_length=8)


class SemanticVerdict(BaseModel):
    verdict: str
    critique: str = ""


class AnalysisResult(BaseModel):
    answer_markdown: str
    key_findings: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    chart_spec: ChartSpec | None = None
