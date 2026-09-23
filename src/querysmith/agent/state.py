"""Typed state and immutable request contracts for the bounded agent."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QueryStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Intent(BaseModel):
    metric: str
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    expected_columns: list[str] = Field(default_factory=list)
    top_n: int | None = Field(default=None, ge=1)
    ambiguity_flags: list[str] = Field(default_factory=list)


class SqlAttempt(BaseModel):
    sql: str
    sql_hash: str
    error_class: str | None = None
    critique: str | None = None


class Budgets(BaseModel):
    max_attempts: int = Field(3, ge=1, le=10)
    max_llm_calls: int = Field(10, ge=1)
    max_tokens: int = Field(60_000, ge=1)
    deadline: datetime
    resource_repairs: int = Field(0, ge=0)
    semantic_repairs: int = Field(0, ge=0)

    @classmethod
    def with_deadline(cls, deadline: datetime) -> "Budgets":
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        return cls(
            max_attempts=3,
            max_llm_calls=10,
            max_tokens=60_000,
            deadline=deadline,
            resource_repairs=0,
            semantic_repairs=0,
        )
