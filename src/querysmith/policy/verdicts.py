"""Typed SQL policy verdicts."""

from enum import StrEnum

from pydantic import BaseModel


class PolicyReason(StrEnum):
    PARSE_ERROR = "parse_error"
    MULTI_STATEMENT = "multi_statement"
    NON_SELECT = "non_select"
    FORBIDDEN_NODE = "forbidden_node"
    SELECT_STAR = "select_star"
    UNAUTHORIZED_TABLE = "unauthorized_table"
    BLOCKED_COLUMN = "blocked_column"
    DENIED_FUNCTION = "denied_function"
    REWRITE_FAILED = "rewrite_failed"


class PolicyVerdict(BaseModel):
    ok: bool
    reason: PolicyReason | None = None
    detail: str | None = None
    normalized_sql: str | None = None
    rewritten_sql: str | None = None
    sql_hash: str | None = None
