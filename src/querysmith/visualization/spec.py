"""Untrusted chart-spec schema and compatibility gate."""

import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from querysmith.execution.executor import ExecutionOutcome


class ChartType(StrEnum):
    BAR = "bar"
    HBAR = "hbar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    TABLE = "table"


class Axis(BaseModel):
    column: str
    label: str = Field(default="", max_length=80)
    aggregation: None = None

    @field_validator("column", "label")
    @classmethod
    def plain_axis_text(cls, value: str) -> str:
        if re.search(r"<[^>]+>|javascript:", value, flags=re.IGNORECASE):
            raise ValueError("HTML and script content are forbidden")
        return value


class ChartSpec(BaseModel):
    chart_type: ChartType
    title: str = Field(max_length=120)
    x: Axis
    y: Axis | None = None
    limit: int = Field(20, ge=1, le=100)

    @field_validator("title")
    @classmethod
    def plain_title(cls, value: str) -> str:
        if re.search(r"<[^>]+>|javascript:", value, flags=re.IGNORECASE):
            raise ValueError("HTML and script content are forbidden")
        return value


class ChartVerdict(BaseModel):
    valid: bool
    spec: ChartSpec | None = None
    warning: str | None = None


def validate_chart(spec: ChartSpec, result: ExecutionOutcome) -> ChartVerdict:
    required = {spec.x.column} | ({spec.y.column} if spec.y else set())
    if not required.issubset(result.columns):
        return ChartVerdict(valid=False, warning="chart references missing columns")
    if result.row_count == 0:
        return ChartVerdict(valid=False, warning="no data to visualize")
    if spec.chart_type is ChartType.PIE and result.row_count > 8:
        return ChartVerdict(
            valid=True,
            spec=spec.model_copy(update={"chart_type": ChartType.BAR}),
            warning="pie downgraded to bar",
        )
    return ChartVerdict(valid=True, spec=spec)
