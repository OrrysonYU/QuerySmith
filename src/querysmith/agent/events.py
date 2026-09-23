"""Safe user-facing trace events."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    QUESTION_INTERPRETED = "QUESTION_INTERPRETED"
    SCHEMA_SELECTED = "SCHEMA_SELECTED"
    SQL_GENERATED = "SQL_GENERATED"
    SQL_VALIDATED = "SQL_VALIDATED"
    QUERY_EXECUTED = "QUERY_EXECUTED"
    QUERY_FAILED = "QUERY_FAILED"
    SQL_REPAIRED = "SQL_REPAIRED"
    RESULT_VALIDATED = "RESULT_VALIDATED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    QUERY_COMPLETED = "QUERY_COMPLETED"
    QUERY_BLOCKED = "QUERY_BLOCKED"


class TraceEvent(BaseModel):
    sequence: int
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float | None = None
    safe_fields: dict[str, Any] = Field(default_factory=dict)
