"""Safe database error classifications."""

from enum import StrEnum

from pydantic import BaseModel


class DatabaseErrorClass(StrEnum):
    SYNTAX = "syntax"
    UNDEFINED_OBJECT = "undefined_object"
    TYPE_MISMATCH = "type_mismatch"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ExecutionError(BaseModel):
    category: DatabaseErrorClass
    sqlstate: str | None = None
    safe_message: str


def normalize_database_exception(exc: Exception) -> ExecutionError:
    sqlstate = getattr(exc, "sqlstate", None)
    prefix = str(sqlstate or "")[:2]
    category = {
        "42": DatabaseErrorClass.SYNTAX,
        "22": DatabaseErrorClass.TYPE_MISMATCH,
        "08": DatabaseErrorClass.UNAVAILABLE,
        "57": DatabaseErrorClass.CANCELLED,
    }.get(prefix, DatabaseErrorClass.UNKNOWN)
    if sqlstate in {"42P01", "42703"}:
        category = DatabaseErrorClass.UNDEFINED_OBJECT
    if sqlstate == "57014":
        category = DatabaseErrorClass.TIMEOUT
    return ExecutionError(
        category=category,
        sqlstate=str(sqlstate) if sqlstate else None,
        safe_message="Database rejected the query.",
    )
