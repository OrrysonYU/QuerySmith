"""Deterministic failure classification and routing."""

from enum import StrEnum

from pydantic import BaseModel

from querysmith.execution.errors import DatabaseErrorClass
from querysmith.policy.verdicts import PolicyReason


class FailureRoute(StrEnum):
    REPAIR = "repair"
    CLARIFY = "clarify"
    BLOCK = "block"
    FAIL = "fail"


class ClassifiedFailure(BaseModel):
    category: str
    route: FailureRoute
    repair_hint: str | None = None


def classify(
    *,
    policy_reason: PolicyReason | None = None,
    database_error: DatabaseErrorClass | None = None,
    semantic_mismatch: bool = False,
) -> ClassifiedFailure:
    if policy_reason in {
        PolicyReason.NON_SELECT,
        PolicyReason.MULTI_STATEMENT,
        PolicyReason.FORBIDDEN_NODE,
        PolicyReason.UNAUTHORIZED_TABLE,
        PolicyReason.BLOCKED_COLUMN,
        PolicyReason.DENIED_FUNCTION,
        PolicyReason.SELECT_STAR,
    }:
        return ClassifiedFailure(category=str(policy_reason), route=FailureRoute.BLOCK)
    if policy_reason is PolicyReason.PARSE_ERROR:
        return ClassifiedFailure(
            category="syntax",
            route=FailureRoute.REPAIR,
            repair_hint="Correct SQL syntax without changing the intent.",
        )
    if database_error in {
        DatabaseErrorClass.SYNTAX,
        DatabaseErrorClass.UNDEFINED_OBJECT,
        DatabaseErrorClass.TYPE_MISMATCH,
    }:
        return ClassifiedFailure(
            category=str(database_error),
            route=FailureRoute.REPAIR,
            repair_hint="Use only the supplied schema and types.",
        )
    if database_error is DatabaseErrorClass.TIMEOUT:
        return ClassifiedFailure(
            category="timeout",
            route=FailureRoute.REPAIR,
            repair_hint="Reduce cost without dropping requested filters.",
        )
    if semantic_mismatch:
        return ClassifiedFailure(
            category="semantic",
            route=FailureRoute.REPAIR,
            repair_hint="Answer the original structured intent exactly.",
        )
    return ClassifiedFailure(category="non_recoverable", route=FailureRoute.FAIL)
