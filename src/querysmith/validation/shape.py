"""Deterministic result-shape and suspicion checks."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from querysmith.agent.state import Intent
from querysmith.execution.executor import ExecutionOutcome


class ShapeStatus(StrEnum):
    OK = "OK"
    SUSPICIOUS = "SUSPICIOUS"
    MISMATCH = "MISMATCH"
    EMPTY = "EMPTY"


class ShapeVerdict(BaseModel):
    status: ShapeStatus
    reasons: list[str] = Field(default_factory=list)


def validate_shape(result: ExecutionOutcome, intent: Intent) -> ShapeVerdict:
    if result.error:
        return ShapeVerdict(status=ShapeStatus.MISMATCH, reasons=["execution_error"])
    if result.row_count == 0:
        return ShapeVerdict(status=ShapeStatus.EMPTY, reasons=["empty_results_are_not_success"])
    missing = sorted(set(intent.expected_columns) - set(result.columns))
    if missing:
        return ShapeVerdict(status=ShapeStatus.MISMATCH, reasons=[f"missing:{','.join(missing)}"])
    if intent.top_n is not None and result.row_count > intent.top_n:
        return ShapeVerdict(status=ShapeStatus.MISMATCH, reasons=["top_n_exceeded"])
    metric_index = result.columns.index(intent.metric) if intent.metric in result.columns else None
    if metric_index is not None:
        values: list[Any] = [row[metric_index] for row in result.rows]
        if values and sum(value is None for value in values) / len(values) > 0.5:
            return ShapeVerdict(status=ShapeStatus.SUSPICIOUS, reasons=["metric_mostly_null"])
        if len(values) > 1 and len({str(value) for value in values}) == 1:
            return ShapeVerdict(status=ShapeStatus.SUSPICIOUS, reasons=["metric_all_identical"])
    return ShapeVerdict(status=ShapeStatus.OK)
