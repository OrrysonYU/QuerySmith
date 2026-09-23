"""Application error contract."""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    QUESTION_INVALID = "QUESTION_INVALID"
    QUERY_BLOCKED_POLICY = "QUERY_BLOCKED_POLICY"
    QUERY_FAILED = "QUERY_FAILED"
    DATASOURCE_UNAVAILABLE = "DATASOURCE_UNAVAILABLE"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    INTERNAL = "INTERNAL"


class QuerySmithError(Exception):
    def __init__(
        self, code: ErrorCode, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.details = details or {}
