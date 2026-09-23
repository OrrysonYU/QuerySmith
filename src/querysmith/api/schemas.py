"""Public API schemas."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    mode: Literal["auto", "async"] = "auto"
    conversation_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)


class ChatResponse(BaseModel):
    query_id: str
    status: str
    result: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
